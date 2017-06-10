#!/usr/bin/env python3

import copy
import datetime
import subprocess
import pprint
import time
import os

import Boolean as MyBoolean

class CTLPolicy:
    def __init__(self, string):
        self.boolean = MyBoolean.Boolean(string)

    def getConditions(self):
        yield from self.boolean.getConditions()

    def getConstraints(self, controller):
        for condition in self.boolean.getConditions():
            yield from condition.getConstraints()

    def getRelatedVariables(self, controller):
        for condition in self.boolean.getConditions():
            yield from condition.getVariables()

    def dumpNumvModel(self, controller):
        string_list = [controller.dumpNumvModel()]
        string_list.append('')
        string_list.append('  SPEC AG ({});'.format(self.boolean.getString()))
        return '\n'.join(string_list)

    def findWhichRules(self, previous_state, current_state, transitions, controller):
        rules = set()

        for device_variable in current_state:
            current_value = current_state[device_variable]
            previous_value = previous_state[device_variable]

            if current_value == previous_value:
                continue

            if device_variable not in transitions:
                rules.add('ENV')
                continue

            for boolean, value, rule_name in transitions[device_variable]:
                if boolean == 'next(attack)' and current_state['attack'] == 'TRUE':
                    rules.add('ATTACK')
                    break

                if controller.checkRuleSatisfied(previous_state, boolean):
                    rules.add(rule_name)
                    break

        return rules

    def parseOutput(self, output, controller):
        index = output.index('-- specification')
        output = output[index:]

        lines = output.splitlines()
        lines = [line.strip() for line in lines]
        if lines[0].endswith('true'):
            return {'result': 'SUCCESS'}

        transitions = controller.getTransitions()
        states = list()
        rules = list()
        current_state = dict()

        # get initial state
        index = 4
        if lines[4].startswith('-- Loop starts here'):
            index += 1

        while index + 1 < len(lines):
            index += 1
            line = lines[index]

            if line.startswith('-> State: 1.2 <-'):
                break

            if line.startswith('-- Loop starts here'):
                continue

            device_variable, value = line.split(' = ')
            current_state[device_variable] = value
        states.append(current_state)

        while index + 1 < len(lines):
            previous_state = current_state
            current_state = copy.copy(previous_state)

            while index + 1 < len(lines):
                index += 1
                line = lines[index]

                if line.startswith('-> State: '):
                    break

                if line.startswith('-- Loop starts here'):
                    continue

                device_variable, value = line.split(' = ')
                current_state[device_variable] = value

            rule = self.findWhichRules(previous_state, current_state, transitions, controller)
            states.append(current_state)
            rules.append(rule)

        return {'result': 'FAILED', 'states': states, 'rules': rules}

    def check(self, controller):
        model = self.dumpNumvModel(controller)
        filename = '/tmp/r04922156/model {0} {2} {1}.smv'.format(os.getppid(), os.getpid(), datetime.datetime.now())
        with open(filename, 'w') as f:
            f.write(model)

        checking_start = time.perf_counter()
        try:
            p = subprocess.run(['NuSMV', '-keep_single_value_vars', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600)
        except subprocess.TimeoutExpired:
            return None, 3600
        checking_time = time.perf_counter() - checking_start

        output = p.stdout.decode('UTF-8')
        result = self.parseOutput(output, controller)

        return result, checking_time



