#!/usr/bin/env python3

import Variable as MyVariable

class Device:
    def __init__(self, channel_name, definition, name):
        self.channel_name = channel_name
        self.definition = definition
        self.name = name
        self.variables = dict()

        # initial each variable
        for variable_name, variable_definition in self.definition['variables'].items():
            variable_type = variable_definition['type']
            if variable_type == 'boolean':
                variable = MyVariable.BooleanVariable(self.name, variable_definition, variable_name)
            elif variable_type == 'set':
                variable = MyVariable.SetVariable(self.name, variable_definition, variable_name)
            elif variable_type == 'range':
                variable = MyVariable.RangeVariable(self.name, variable_definition, variable_name)
            else:
                raise TypeError('Unknown variables')

            self.variables[variable_name] = variable

    def getPossibleValuesOfVariables(self):
        possible_values_of_variables = dict()
        for variable_name, variable in self.variables.items():
            possible_values = variable.getPossibleValues()
            possible_values_of_variables[variable_name] = possible_values

        return possible_values_of_variables

    def setState(self, state):
        for variable_name, value in state.items():
            variable = self.variables[variable_name]
            variable.setValue(value)

    def getVariableNames(self):
        return set(self.variables.keys())

    def getVariable(self, variable_name):
        return self.variables[variable_name]

    def hasVariable(self, variable_name):
        return variable_name in self.variables

    def addCustomRules(self, controller):
        if 'customs' not in self.definition:
            return

        device_names = set(device_name for device_name, variable_name in controller.device_variables)
        if self.name not in device_names:
            return

        for custom_rule in self.definition['customs']:
            rule_name = custom_rule['name']

            trigger_channel_name = self.channel_name
            trigger_name = '{}_trigger'.format(rule_name)
            trigger_definition = {
                'input': [{'type': 'device', 'device':[self.channel_name]}],
                'definition': {'boolean': custom_rule['trigger']}
            }
            trigger_inputs = [self.name]

            action_channel_name = self.channel_name
            action_name = '{}_action'.format(rule_name)
            action_definition = {
                'input': [{'type': 'device', 'device': [self.channel_name]}],
                'definition': custom_rule['action']
            }
            action_inputs = [self.name]

            controller.addCustomRule(rule_name,
                trigger_channel_name, trigger_name, trigger_definition, trigger_inputs,
                action_channel_name, action_name, action_definition, action_inputs)

    @property
    def pruned(self):
        for variable_name, variable in self.variables.items():
            if not variable.pruned:
                return False

        return True

