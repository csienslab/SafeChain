#!/usr/bin/env python3

import Boolean as MyBoolean

class PrivacyPolicy:
    def __init__(self, variables):
        self.variables = variables

    def getConstraints(self, controller):
        for rule in controller.rules:
            for condition in rule.getConditions():
                for device_name, variable_name, operator, value in condition.getConstraints():
                    if operator != '←':
                        continue

                    if (device_name, variable_name) not in self.variables:
                        continue

                    yield (device_name, variable_name, operator, value)

    def getRelatedVariables(self):
        yield from self.variables

    def dumpNumvModel(self, controller):
        string = controller.dumpNumvModel(name='home', init=False)
        string += '\n'
        string += 'MODULE main\n'
        string += '  VAR\n'
        string += '    a: home;\n'
        string += '    b: home;\n'
        string += '\n'

        vulnerables = ['next(a.{0}.{1}) = next(b.{0}.{1})'.format(device_name, variable_name)
                       for device_name, variable_name in controller.vulnerables
                       if not controller.getDevice(device_name).getVariable(variable_name).pruned]
        string += '  INVAR a.attack = b.attack;\n'
        string += '  TRANS a.attack != TRUE | ({});\n'.format(' & '.join(vulnerables))
        string += '\n'

        vulnerables = ['a.{0}.{1} = b.{0}.{1}'.format(device_name, variable_name)
                       for device_name, variable_name in controller.vulnerables
                       if not controller.getDevice(device_name).getVariable(variable_name).pruned]
        string += '  INVARSPEC {};\n'.format(' & '.join(vulnerables))
        return string


