#!/usr/bin/env python3

import re
import copy
import datetime
import subprocess
import pprint
import time
import os
import networkx
import tempfile

import SafeChain.Boolean as MyBoolean
import SafeChain.InvariantPolicy as MyInvariantPolicy

class PrivacyPolicy:
    def __init__(self, variables):
        self.variables = variables
        self.variable_pattern = re.compile('\w+\.\w+')
        self.random_pattern = re.compile('{.+}|-?\d+\.\.-?\d+')
        self.test = 0

    def getConditions(self):
        return iter([])

    def getConstraints(self, controller):
        for rule in controller.rules:
            for condition in rule.getConditions():
                for channel_name, variable_name, operator, value in condition.getConstraints():
                    if operator != '←':
                        continue

                    if (channel_name, variable_name) not in controller.vulnerables:
                        continue

                    yield (channel_name, variable_name, operator, value)

    def getRelatedVariables(self, controller, graph):
        affected = set()
        for channel_variable in self.variables:
            if channel_variable in graph:
                affected.add(channel_variable)
                affected.update(networkx.descendants(graph, channel_variable))

        yield from controller.vulnerables & affected

    def getBooleanPrepend(self, boolean, prepend):
        tokens = boolean.split(' ')
        tokens = ['{0}{1}'.format(prepend, token)
                  if self.variable_pattern.fullmatch(token) else token
                  for token in tokens]
        return ' '.join(tokens)

    def getRandomTransitionConstraint(self, previous, channel_variable):
        """
        boolean1 == FALSE and boolean2 == FALSE and boolean3 == TRUE => next()
        boolean1 != FALSE or  boolean2 != FALSE or  boolean3 != TRUE or next()
        boolean1 or boolean2 or !boolean3 or next()
        """
        result = list()
        for boolean in previous[:-1]:
            if boolean == 'next(attack)':
                a = 'next(a.attack)'
                b = 'next(b.attack)'
            else:
                a = self.getBooleanPrepend(boolean, 'a.')
                b = self.getBooleanPrepend(boolean, 'b.')
            result.append('({0}) | ({1})'.format(a, b))

        if previous[-1] == 'next(attack)':
            a = 'next(a.attack)'
            b = 'next(b.attack)'
        else:
            a = self.getBooleanPrepend(previous[-1], 'a.')
            b = self.getBooleanPrepend(previous[-1], 'b.')
        result.append('!({0}) | !({1})'.format(a, b))

        result.append('next(a.{0}) = next(b.{0})'.format(channel_variable))
        return ' | '.join(result)

    def getRandomTransitions(self, controller):
        transitions = controller.getTransitions()
        high_variables = set('{}.{}'.format(channel_name, variable_name) for channel_name, variable_name in self.variables)

        for channel_variable in transitions:
            if channel_variable in high_variables:
                # H value variables
                continue

            previous = list()
            for boolean, value, rule_name in transitions[channel_variable]:
                previous.append(boolean)

                if not self.random_pattern.fullmatch(value):
                    continue

                yield self.getRandomTransitionConstraint(previous, channel_variable)

    def dumpNumvModel(self, controller):
        string_list = [controller.dumpNumvModel(name='home', init=False)]
        string_list.append('')
        string_list.append('MODULE main')
        string_list.append('  VAR')
        string_list.append('    a: home;')
        string_list.append('    b: home;')
        string_list.append('')

        string_list.append('  ASSIGN')
        for channel_name in sorted(controller.channels):
            channel = controller.channels[channel_name]
            for variable_name in sorted(channel.variables):
                if (channel_name, variable_name) not in controller.channel_variables:
                    continue

                variable = channel.variables[variable_name]
                if variable.pruned:
                    continue

                value = variable.getEquivalentActionCondition(variable.value)
                string_list.append('    init(a.{0}.{1}):= {2};'.format(channel_name, variable_name, value))
        string_list.append('    -- {}'.format(self.variables))
        string_list.append('')

        middle_and_lows = ['a.{0}.{1} = b.{0}.{1}'.format(channel_name, variable_name)
                           for channel_name, channel in controller.channels.items()
                           for variable_name in channel.getVariableNames()
                           if (channel_name, variable_name) not in self.variables
                           and (channel_name, variable_name) in controller.channel_variables
                           and not channel.getVariable(variable_name).pruned]
        if len(middle_and_lows) != 0:
            string_list.append('  INIT {};'.format(' & '.join(middle_and_lows)))

        string_list.append('  INVAR a.attack = b.attack;')

        transitions = controller.getTransitions()
        sensors = ['{0}.{1}'.format(channel_name, variable_name)
                   for channel_name, channel in controller.channels.items()
                   for variable_name in channel.getVariableNames()
                   if '{0}.{1}'.format(channel_name, variable_name) not in transitions
                   and (channel_name, variable_name) not in self.variables
                   and (channel_name, variable_name) in controller.channel_variables
                   and not channel.getVariable(variable_name).pruned]
        sensors = ['a.{0} = b.{0}'.format(sensor) for sensor in sensors]
        if len(sensors) != 0:
            string_list.append('  INVAR {0};'.format(' & '.join(sensors)))

        for constraint in self.getRandomTransitions(controller):
            string_list.append('  TRANS {0};'.format(constraint))
        string_list.append('')

        vulnerables = ['a.{0}.{1} = b.{0}.{1}'.format(channel_name, variable_name)
                       for channel_name, variable_name in controller.vulnerables
                       if not controller.getChannel(channel_name).getVariable(variable_name).pruned
                       and (channel_name, variable_name) in controller.channel_variables]
        if len(vulnerables) != 0:
            string_list.append('  INVARSPEC {};'.format(' & '.join(vulnerables)))
        else:
            string_list.append('  INVARSPEC TRUE;')

        return '\n'.join(string_list)

    def findWhichRules(self, states, transitions, controller):
        rule_list = list()

        for previous_state, current_state in zip(states, states[1:]):
            rules = set()

            for channel_variable in current_state:
                current_value = current_state[channel_variable]
                previous_value = previous_state[channel_variable]

                if current_value == previous_value:
                    continue

                if channel_variable not in transitions:
                    rules.add('ENV')
                    continue

                for boolean, value, rule_name in transitions[channel_variable]:
                    if boolean == 'next(attack)' and current_state['attack'] == 'TRUE':
                        rules.add('ATTACK')
                        break

                    if controller.checkRuleSatisfied(previous_state, boolean):
                        rules.add(rule_name)
                        break

            rule_list.append(rules)

        return rule_list

    def parseOutput(self, output, controller, filename):
        try:
            index = output.index('-- ')
        except ValueError:
            print('Unexpected output:', filename)
            return {'result': 'UNKNOWN'}
        output = output[index:]

        lines = output.splitlines()
        lines = [line.strip() for line in lines]

        if lines[0].endswith('true'):
            return {'result': 'SUCCESS'}


        states_A = list()
        current_state_A = dict()

        states_B = list()
        current_state_B = dict()

        # get initial state
        index = 4
        while index + 1 < len(lines):
            index += 1
            line = lines[index]

            if line.startswith('-> State: 1.2 <-'):
                break

            channel_variable, value = line.split(' = ')
            if channel_variable.startswith('a.'):
                current_state_A[channel_variable[2:]] = value
            else:
                current_state_B[channel_variable[2:]] = value
        states_A.append(current_state_A)
        states_B.append(current_state_B)

        while index + 1 < len(lines):
            previous_state_A = current_state_A
            current_state_A = copy.copy(previous_state_A)
            previous_state_B = current_state_B
            current_state_B = copy.copy(previous_state_B)

            while index + 1 < len(lines):
                index += 1
                line = lines[index]

                if line.startswith('-> State: '):
                    break

                channel_variable, value = line.split(' = ')
                if channel_variable.startswith('a.'):
                    current_state_A[channel_variable[2:]] = value
                else:
                    current_state_B[channel_variable[2:]] = value

            states_A.append(current_state_A)
            states_B.append(current_state_B)

        return {'result': 'FAILED', 'states_A': states_A, 'states_B': states_B}

    def checkReachable(self, controller, state):
        boolean = ' & '.join('{0} = {1}'.format(channel_variable, state[channel_variable]) for channel_variable in sorted(state) if channel_variable != 'attack')
        boolean = '! ( {0} )'.format(boolean)
        policy = MyInvariantPolicy.InvariantPolicy(boolean)
        return controller.check(policy, custom=False, pruning=None, grouping=None)

    def check(self, controller, timeout, bmc):
        total_checking_time = 0
        transitions = controller.getTransitions()
        model = self.dumpNumvModel(controller) + '\n'

        while True:
            _, filename = tempfile.mkstemp(suffix='.smv')
            with open(filename, 'w') as f:
                f.write(model)

            checking_start = time.perf_counter()
            try:
                cmds = ['NuSMV', '-keep_single_value_vars'] + (['-bmc'] if bmc else []) + [filename]
                p = subprocess.run(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            except subprocess.TimeoutExpired:
                return filename, None, timeout
            total_checking_time += time.perf_counter() - checking_start

            if total_checking_time >= timeout:
                return filename, None, timeout

            output = p.stdout.decode('UTF-8')
            result = self.parseOutput(output, controller, filename)
            if result['result'] != 'SUCCESS':
                result['rules_A'] = self.findWhichRules(result['states_A'], transitions, controller)
                result['rules_B'] = self.findWhichRules(result['states_B'], transitions, controller)
            return filename, result, total_checking_time
