#!/usr/bin/env python3

import re
import copy
import datetime
import subprocess
import pprint

import Boolean as MyBoolean
import InvariantPolicy as MyInvariantPolicy

class PrivacyPolicy:
    def __init__(self, variables):
        self.variables = variables
        self.variable_pattern = re.compile('\w+\.\w+')
        self.random_pattern = re.compile('{.+}|-?\d+\.\.-?\d+')

    def getConditions(self):
        return iter([])

    def getConstraints(self, controller):
        for rule in controller.rules:
            for condition in rule.getConditions():
                for device_name, variable_name, operator, value in condition.getConstraints():
                    if operator != '←':
                        continue

                    if (device_name, variable_name) not in controller.vulnerables:
                        continue

                    yield (device_name, variable_name, operator, value)

    def getRelatedVariables(self, controller):
        yield from controller.vulnerables

    def getBooleanPrepend(self, boolean, prepend):
        tokens = boolean.split(' ')
        tokens = ['{0}{1}'.format(prepend, token)
                  if self.variable_pattern.fullmatch(token) else token
                  for token in tokens]
        return ' '.join(tokens)

    def getRandomTransitionConstraint(self, previous, device_variable):
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

        result.append('next(a.{0}) = next(b.{0})'.format(device_variable))
        return ' | '.join(result)

    def getRandomTransitions(self, controller):
        transitions = controller.getTransitions()

        for device_variable in transitions:
            previous = list()
            for boolean, value, rule_name in transitions[device_variable]:
                previous.append(boolean)

                if not self.random_pattern.fullmatch(value):
                    continue

                yield self.getRandomTransitionConstraint(previous, device_variable)

    def dumpNumvModel(self, controller, invalid_states):
        string = controller.dumpNumvModel(name='home', init=False)
        string += '\n'
        string += 'MODULE main\n'
        string += '  VAR\n'
        string += '    a: home;\n'
        string += '    b: home;\n'
        string += '\n'

        middle_and_lows = ['a.{0}.{1} = b.{0}.{1}'.format(device_name, variable_name)
                           for device_name, device in controller.devices.items()
                           for variable_name in device.getVariableNames()
                           if (device_name, variable_name) not in self.variables
                           and (device_name, variable_name) in controller.device_variables
                           and not device.getVariable(variable_name).pruned]
        if len(middle_and_lows) != 0:
            string += '  INIT {};\n'.format(' & '.join(middle_and_lows))

        for state_A, state_B in invalid_states:
            boolean = ' & '.join('a.{0} = {1} & b.{0} = {2}'.format(device_variable, state_A[device_variable], state_B[device_variable]) for device_variable in sorted(state_A) if device_variable != 'attack')
            string += '  INIT ! ( {0} )\n'.format(boolean)
            boolean = ' & '.join('a.{0} = {1} & b.{0} = {2}'.format(device_variable, state_B[device_variable], state_A[device_variable]) for device_variable in sorted(state_B) if device_variable != 'attack')
            string += '  INIT ! ( {0} )\n'.format(boolean)

        string += '  INVAR a.attack = b.attack;\n'

        transitions = controller.getTransitions()
        sensors = ['{0}.{1}'.format(device_name, variable_name)
                   for device_name, device in controller.devices.items()
                   for variable_name in device.getVariableNames()
                   if '{0}.{1}'.format(device_name, variable_name) not in transitions
                   and (device_name, variable_name) in controller.device_variables
                   and not device.getVariable(variable_name).pruned]
        sensors = ['a.{0} = b.{0}'.format(sensor) for sensor in sensors]
        if len(sensors) != 0:
            string += '  INVAR {0};\n'.format(' & '.join(sensors))

        for constraint in self.getRandomTransitions(controller):
            string += '  TRANS {0};\n'.format(constraint)
        string += '\n'

        vulnerables = ['a.{0}.{1} = b.{0}.{1}'.format(device_name, variable_name)
                       for device_name, variable_name in controller.vulnerables
                       if not controller.getDevice(device_name).getVariable(variable_name).pruned
                       and (device_name, variable_name) in controller.device_variables]
        if len(vulnerables) != 0:
            string += '  INVARSPEC {};\n'.format(' & '.join(vulnerables))
        else:
            string += '  INVARSPEC TRUE;\n'
        return string

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
        index = output.index('-- invariant')
        output = output[index:]

        lines = output.splitlines()
        if lines[0].endswith('true'):
            return {'result': 'SUCCESS'}

        transitions = controller.getTransitions()

        states_A = list()
        rules_A = list()
        current_state_A = dict()

        states_B = list()
        rules_B = list()
        current_state_B = dict()

        # get initial state
        index = 4
        while index + 1 < len(lines):
            index += 1
            line = lines[index].strip()

            if line.startswith('-> State: 1.2 <-'):
                break

            device_variable, value = line.split(' = ')
            if device_variable.startswith('a.'):
                current_state_A[device_variable[2:]] = value
            else:
                current_state_B[device_variable[2:]] = value
        states_A.append(current_state_A)
        states_B.append(current_state_B)

        while index + 1 < len(lines):
            previous_state_A = current_state_A
            current_state_A = copy.copy(previous_state_A)
            previous_state_B = current_state_B
            current_state_B = copy.copy(previous_state_B)

            while index + 1 < len(lines):
                index += 1
                line = lines[index].strip()

                if line.startswith('-> State: '):
                    break

                device_variable, value = line.split(' = ')
                if device_variable.startswith('a.'):
                    current_state_A[device_variable[2:]] = value
                else:
                    current_state_B[device_variable[2:]] = value

            rule_A = self.findWhichRules(previous_state_A, current_state_A, transitions, controller)
            states_A.append(current_state_A)
            rules_A.append(rule_A)

            rule_B = self.findWhichRules(previous_state_B, current_state_B, transitions, controller)
            states_B.append(current_state_B)
            rules_B.append(rule_B)

        return {'result': 'FAILED', 'states_A': states_A, 'rules_A': rules_A, 'states_B': states_B, 'rules_B': rules_B}

    def checkReachable(self, controller, state):
        boolean = ' & '.join('{0} = {1}'.format(device_variable, state[device_variable]) for device_variable in sorted(state) if device_variable != 'attack')
        boolean = '! ( {0} )'.format(boolean)
        policy = MyInvariantPolicy.InvariantPolicy(boolean)
        result = controller.check(policy, custom=False, pruning=None, grouping=None)
        if result['result'] == 'FAILED':
            return result
        else:
            return False

    def check(self, controller):
        invalid_states = list()
        while True:
            model = self.dumpNumvModel(controller, invalid_states)
            filename = '/tmp/model {}.smv'.format(datetime.datetime.now())
            with open(filename, 'w') as f:
                f.write(model)

            p = subprocess.run(['NuSMV', '-keep_single_value_vars', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.stdout.decode('UTF-8')
            result = self.parseOutput(output, controller)
            if result['result'] == 'SUCCESS':
                return result

            path = self.checkReachable(controller, result['states_A'][0])
            if path:
                result['states'] = path['states']
                result['rules'] = path['rules']
                return result

            path = self.checkReachable(controller, result['states_B'][0])
            if path:
                result['states'] = path['states']
                result['rules'] = path['rules']
                return result

            invalid_states.append((result['states_A'][0], result['states_B'][0]))

