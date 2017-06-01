#!/usr/bin/env python3

import re
import Boolean as MyBoolean

class PrivacyPolicy:
    def __init__(self, variables):
        self.variables = variables
        self.variable_pattern = re.compile('\w+\.\w+')
        self.random_pattern = re.compile('{.+}|-?\d+\.\.-?\d+')

    def getConditions(self):
        raise StopIteration

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

    def dumpNumvModel(self, controller):
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
                           and not device.getVariable(variable_name).pruned]
        if len(middle_and_lows) != 0:
            string += '  INIT {};\n'.format(' & '.join(middle_and_lows))

        string += '  INVAR a.attack = b.attack;\n'

        transitions = controller.getTransitions()
        sensors = ['{0}.{1}'.format(device_name, variable_name)
                   for device_name, device in controller.devices.items()
                   for variable_name in device.getVariableNames()
                   if '{0}.{1}'.format(device_name, variable_name) not in transitions
                   and not device.getVariable(variable_name).pruned]
        sensors = ['a.{0} = b.{0}'.format(sensor) for sensor in sensors]
        string += '  INVAR {0};\n'.format(' & '.join(sensors))

        for constraint in self.getRandomTransitions(controller):
            string += '  TRANS {0};\n'.format(constraint)
        string += '\n'

        vulnerables = ['a.{0}.{1} = b.{0}.{1}'.format(device_name, variable_name)
                       for device_name, variable_name in controller.vulnerables
                       if not controller.getDevice(device_name).getVariable(variable_name).pruned]
        string += '  INVARSPEC {};\n'.format(' & '.join(vulnerables))
        return string

    def parseOutput(self, output):
        pass

