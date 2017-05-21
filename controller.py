#!/usr/bin/env python3

# TODO
# rules attached to variables and devices
# divide using set

import pickle
import collections
import random
import re

import Device as MyDevice
import Trigger as MyTrigger
import Action as MyAction
import Rule as MyRule

class Controller:
    def __init__(self, database):
        self.database = database

        self.devices = dict()
        self.rules = collections.OrderedDict()

    def getFeasibleDevices(self):
        return self.database.items()

    def addDevice(self, device):
        device_name = device.name
        self.devices[device_name] = device

    def getFeasibleInputs(self, input_definitions, parameters):
        index = len(parameters)
        if index >= len(input_definitions):
            return None

        input_definition = input_definitions[index]
        input_type = input_definition['type']

        if input_type == 'device':
            device_type = set(input_definition['device'])
            feasible_inputs = set(device_name for device_name, device in self.devices.items() if device.channel_name in device_type)
        elif input_type == 'variable':
            device_name = input_definition['device'].format(*parameters)
            device = self.devices[device_name]
            feasible_inputs = device.getVariableNames()
        elif input_type == 'value':
            device_name = input_definition['device'].format(*parameters)
            variable_name = input_definition['variable'].format(*parameters)

            device = self.devices[device_name]
            variable = device.getVariable(variable_name)
            feasible_inputs = variable.getPossibleValues()
        elif input_type == 'set':
            feasible_inputs = set(input_definition['setValue'])
        else:
            raise TypeError('Unknown input type')

        exceptions = set(input_definition['exceptions']) if 'exceptions' in input_definition else set()
        return feasible_inputs - exceptions

    def getFeasibleInputsForTrigger(self, channel_name, trigger_name):
        input_definitions = self.database[channel_name]['triggers'][trigger_name]['input']
        parameters = list()

        feasible_inputs = self.getFeasibleInputs(input_definitions, parameters)
        while feasible_inputs != None:
            feasible_input = random.choice(tuple(feasible_inputs))
            parameters.append(feasible_input)
            feasible_inputs = self.getFeasibleInputs(input_definitions, parameters)

        return tuple(parameters)

    def getFeasibleInputsForAction(self, channel_name, action_name):
        input_definitions = self.database[channel_name]['actions'][action_name]['input']
        parameters = list()

        feasible_inputs = self.getFeasibleInputs(input_definitions, parameters)
        while feasible_inputs != None:
            feasible_input = random.choice(tuple(feasible_inputs))
            parameters.append(feasible_input)
            feasible_inputs = self.getFeasibleInputs(input_definitions, parameters)

        return tuple(parameters)

    def addRule(self, rule_name,
                trigger_channel_name, trigger_name, trigger_inputs,
                action_channel_name, action_name, action_inputs):
        trigger_definition = self.database[trigger_channel_name]['triggers'][trigger_name]
        trigger = MyTrigger.Trigger(rule_name, trigger_channel_name, trigger_definition, trigger_name, trigger_inputs)
        action_definition = self.database[action_channel_name]['actions'][action_name]
        action = MyAction.Action(rule_name, action_channel_name, action_definition, action_name, action_inputs)

        rule = MyRule.Rule(rule_name, trigger, action)
        self.rules[rule_name] = rule

    def addCustomRule(self, rule_name,
                      trigger_channel_name, trigger_name, trigger_definition, trigger_inputs,
                      action_channel_name, action_name, action_definition, action_inputs):
        trigger = MyTrigger.Trigger(rule_name, trigger_channel_name, trigger_definition, trigger_name, trigger_inputs)
        action = MyAction.Action(rule_name, action_channel_name, action_definition, action_name, action_inputs)

        rule = MyRule.Rule(rule_name, trigger, action)
        self.rules[rule_name] = rule

    def hasVariable(self, device_name, variable_name):
        if device_name not in self.devices:
            return False

        device = self.devices[device_name]
        return device.hasVariable(variable_name)

    def getDevice(self, device_name):
        if device_name not in self.devices:
            return None

        return self.devices[device_name]

    def getVariableTransition(self, device_name, variable_name):
        target = '{0}.{1}'.format(device_name, variable_name)
        for rule_name, rule in self.rules.items():
            for boolean, variable, value in rule.getTransitions():
                if variable == target:
                    yield (boolean, value)

    def toNuSMVModel(self):
        string = ''

        device_names = sorted(self.devices.keys())
        device_names_string = ', '.join(device_names)
        for device_name in device_names:
            device = self.devices[device_name]

            module_name = device_name.upper()
            string += 'MODULE {0}({1})\n'.format(module_name, device_names_string)

            # define variables
            string += '  VAR\n'
            for variable_name in sorted(device.getVariableNames()):
                variable = device.getVariable(variable_name)
                variable_range = variable.getPossibleGroupsInNuSMV()
                string += '    {0}: {1};\n'.format(variable_name, variable_range)

                if variable.previous:
                    string += '    {0}: {1};\n'.format(variable_name+'_previous', variable_range)

            # initial conditions
            string += '  ASSIGN\n'
            for variable_name in sorted(device.getVariableNames()):
                variable = device.getVariable(variable_name)
                value = variable.getEquivalentActionCondition(variable.value)
                string += '    init({0}):= {1};\n'.format(variable_name, value)

                if variable.previous:
                    string += '    init({0}):= {1};\n'.format(variable_name + '_previous', value)

            # rules
            string += '  ASSIGN\n'
            for variable_name in sorted(device.getVariableNames()):
                variable = device.getVariable(variable_name)
                if variable.previous:
                    string += '    next({0}):= {1};\n'.format(variable_name + '_previous', variable_name)

                rules = list(self.getVariableTransition(device_name, variable_name))
                if variable.reset_value != None:
                    value = variable.getEquivalentActionCondition(variable.reset_value)
                    rules.append(('TRUE', value))

                if len(rules) == 0:
                    continue

                if len(rules) == 1:
                    boolean, value = rules[0]
                    if boolean == 'TRUE':
                        string += '    next({0}):= {1};\n'.format(variable_name, value)
                    else:
                        string += '    next({0}):= {1} ? {2}: {0};\n'.format(variable_name, boolean, value)
                elif len(rules) == 2 and rules[-1][0] == 'TRUE':
                    string += '    next({0}):= {1} ? {2}: {3};\n'.format(variable_name, rules[0][0], rules[0][1], rules[1][1])
                else:
                    string += '    next({0}):=\n'.format(variable_name)
                    string += '      case\n'
                    for boolean, value in rules:
                        string += '        {0}: {1};\n'.format(boolean, value)
                    if rules[-1][0] != 'TRUE':
                        string += '        {0}: {1};\n'.format('TRUE', variable_name)
                    string += '      esac;\n'

            string += '\n'

        string += 'MODULE main\n'
        string += '  VAR\n'
        for device_name in device_names:
            module_name = device_name.upper()
            string += '    {0}: {1}({2});\n'.format(device_name, module_name, device_names_string)

        print(string)

    def check(self, grouping=False, pruning=False):
        for device_name, device in self.devices.items():
            device.addCustomRules(self)

        for rule_name, rule in self.rules.items():
            for condition in rule.getConditions():
                for device_name, variable_name, operator, value in condition.getConstraints(self):
                    if operator == '←':
                        continue

                    device = self.devices[device_name]
                    variable = device.getVariable(variable_name)
                    variable.addConstraint(operator, value)

        for device_name, device in self.devices.items():
            for variable_name, variable in device.variables.items():
                variable.setGrouping(True)

        for rule_name, rule in self.rules.items():
            for condition in rule.getConditions():
                condition.toEquivalentCondition(self)

        self.toNuSMVModel()


#         string = ''
# 
#         all_devices_name = sorted(set(device_name for devices in self.channels.values() for device_name in devices.keys()))
# 
#         for channel_name in sorted(self.channels.keys()):
#             channel = self.database[channel_name]
#             devices = self.channels[channel_name]
# 
#             for device_name in sorted(devices.keys()):
#                 device_state = devices[device_name]
#                 string += channel.toNuSMVformat(self.database, device_name, device_state, self.rules, all_devices_name, grouping, self.variable_constraints)
# 
#                 string += '\n'
# 
#         # main module
#         string += 'MODULE main\n'
#         string += '  VAR\n'
# 
#         # initial each devices
#         for channel_name in sorted(self.channels.keys()):
#             channel = self.database[channel_name]
#             devices = self.channels[channel_name]
# 
#             for device_name in sorted(devices.keys()):
#                 module_name = channel.getModuleName(device_name)
#                 string += '    {0}: {1}({2});\n'.format(device_name, module_name, ', '.join(all_devices_name))
#         string += '\n'
# 
#         print(string)



if __name__ == '__main__':
    # load database
    with open('database.dat', 'rb') as f:
        database = pickle.load(f)

    # initial controller
    controller = Controller(database)

    # add devices
    for channel_name, channel_definition in controller.getFeasibleDevices():
        name = re.sub('[^A-Za-z0-9_]+', '', channel_name).lower()
        device = MyDevice.Device(channel_name, channel_definition, name)

        possible_values_of_variables = device.getPossibleValuesOfVariables()
        state = dict((variable_name, random.choice(tuple(possible_values))) for variable_name, possible_values in possible_values_of_variables.items())
        device.setState(state)

        controller.addDevice(device)

    # add rules
    # with open('dataset/coreresultsMay16.tsv', 'r') as f:
    #     all_channels = controller.database.keys()
    #     count = 1
    #     for line in f:
    #         line = line.strip()
    #         columns = line.split('\t')
    #         trigger_channel_name = columns[5]
    #         trigger_name = columns[6]
    #         action_channel_name = columns[8]
    #         action_name = columns[9]
    #         if trigger_channel_name in all_channels and action_channel_name in all_channels:
    #             rule_name = 'RULE{}'.format(count)
    #             trigger_inputs = controller.getFeasibleInputsForTrigger(trigger_channel_name, trigger_name)
    #             action_inputs = controller.getFeasibleInputsForAction(action_channel_name, action_name)
    #             controller.addRule(rule_name, trigger_channel_name, trigger_name, trigger_inputs, action_channel_name, action_name, action_inputs)
    #             count += 1

    rule_name = 'RULE1'
    trigger_channel_name = 'Android Device'
    trigger_name = 'Connects or disconnects from a specific WiFi network'
    action_channel_name = 'WeMo Insight Switch'
    action_name = 'Toggle on/off'

    trigger_inputs = controller.getFeasibleInputsForTrigger(trigger_channel_name, trigger_name)
    action_inputs = controller.getFeasibleInputsForAction(action_channel_name, action_name)
    controller.addRule(rule_name, trigger_channel_name, trigger_name, trigger_inputs, action_channel_name, action_name, action_inputs)

    rule_name = 'RULE2'
    trigger_channel_name = 'WeMo Insight Switch'
    trigger_name = 'Switched on'
    action_channel_name = 'Adafruit'
    action_name = 'Send data to Adafruit IO'

    trigger_inputs = controller.getFeasibleInputsForTrigger(trigger_channel_name, trigger_name)
    action_inputs = controller.getFeasibleInputsForAction(action_channel_name, action_name)
    controller.addRule(rule_name, trigger_channel_name, trigger_name, trigger_inputs, action_channel_name, action_name, action_inputs)

    controller.check(grouping=True)

