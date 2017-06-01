#!/usr/bin/env python3

# TODO
# rules attached to variables and devices
# divide using set
# combine boolean into set
# class sensor and actuator if without rules all possible
# use str.join instead of +
# [80%] assign variable with variable using same constraints
# using subrule and rule for multicondition

import pickle
import collections
import random
import re
import networkx
import subprocess
import datetime
import pprint

import Device as MyDevice
import Trigger as MyTrigger
import Action as MyAction
import Rule as MyRule
import InvariantPolicy as MyInvariantPolicy
import PrivacyPolicy as MyPrivacyPolicy

class Controller:
    def __init__(self, database):
        self.database = database

        self.devices = dict()
        self.rules = list()
        self.vulnerables = set()

    def getFeasibleDevices(self):
        return self.database.items()

    def addDevice(self, device):
        device_name = device.name
        self.devices[device_name] = device

    def addVulnerableDevice(self, device_name):
        if device_name not in self.devices:
            return False

        device = self.devices[device_name]
        for variable_name in device.getVariableNames():
            self.vulnerables.add((device_name, variable_name))

        return True

    def addVulnerableDeviceVariable(self, device_name, variable_name):
        if device_name not in self.devices:
            return False

        device = self.devices[device_name]
        if variable_name not in device.getVariableNames():
            return False

        self.vulnerables.add((device_name, variable_name))
        return True

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
        self.rules.append(rule)

    def addCustomRule(self, rule_name,
                      trigger_channel_name, trigger_name, trigger_definition, trigger_inputs,
                      action_channel_name, action_name, action_definition, action_inputs):
        trigger = MyTrigger.Trigger(rule_name, trigger_channel_name, trigger_definition, trigger_name, trigger_inputs)
        action = MyAction.Action(rule_name, action_channel_name, action_definition, action_name, action_inputs)

        rule = MyRule.Rule(rule_name, trigger, action)
        self.rules.append(rule)

    def getDevice(self, device_name):
        if device_name not in self.devices:
            return None

        return self.devices[device_name]

    def getTransitions(self):
        transitions = collections.defaultdict(list)

        # add rule
        for rule in self.rules:
            for boolean, device_variable, value in rule.getTransitions():
                device_name, variable_name = device_variable.split('.')
                device = self.devices[device_name]
                variable = device.getVariable(variable_name)
                if variable.pruned:
                    continue

                transitions[device_variable].append((boolean, value, rule.name))

        # add reset value
        for device_name, device in self.devices.items():
            for variable_name, variable in device.variables.items():
                if variable.pruned:
                    continue
                if variable.reset_value == None:
                    continue

                value = variable.getEquivalentActionCondition(variable.reset_value)
                device_variable = '{0}.{1}'.format(device_name, variable_name)
                if device_variable not in transitions:
                    # because no rules
                    continue

                transitions[device_variable].append(('TRUE', str(value), 'RESET'))

        # add attack
        for device_name, variable_name in self.vulnerables:
            device = self.devices[device_name]
            variable = device.getVariable(variable_name)
            if variable.pruned:
                continue

            device_variable = '{0}.{1}'.format(device_name, variable_name)
            if device_variable not in transitions:
                # because no rules
                continue

            variable_range = variable.getPossibleGroupsInNuSMV()
            transitions[device_variable].insert(0, ('next(attack)', variable_range, 'ATTACK'))

        return transitions

    def checkRuleSatisfied(self, state, rule_condition):
        string_list = list()

        device_names = sorted(device_name for device_name, device in self.devices.items() if not device.pruned)
        device_names_string = ', '.join(['attack'] + device_names)

        for device_name in device_names:
            device = self.devices[device_name]

            module_name = device_name.upper()
            string_list.append('MODULE {0}({1})'.format(module_name, device_names_string))

            # define variables
            string_list.append('  FROZENVAR')
            for variable_name in sorted(device.getVariableNames()):
                variable = device.getVariable(variable_name)
                if variable.pruned:
                    continue

                variable_range = variable.getPossibleGroupsInNuSMV()
                string_list.append('    {0}: {1};'.format(variable_name, variable_range))

            # initial conditions
            string_list.append('  ASSIGN')
            for variable_name in sorted(device.getVariableNames()):
                variable = device.getVariable(variable_name)
                if variable.pruned:
                    continue

                value = state['{0}.{1}'.format(device_name, variable_name)]
                string_list.append('    init({0}):= {1};'.format(variable_name, value))
            string_list.append('')

        string_list.append('MODULE main')
        string_list.append('  VAR')
        for device_name in device_names:
            module_name = device_name.upper()
            string_list.append('    {0}: {1}({2});'.format(device_name, module_name, device_names_string))

        string_list.append('')
        string_list.append('    attack: boolean;')
        string_list.append('')
        string_list.append('  ASSIGN attack := FALSE;')
        string_list.append('')
        string_list.append('  INVARSPEC {};'.format(rule_condition))

        model = '\n'.join(string_list)

        filename = '/tmp/state {}.smv'.format(datetime.datetime.now())
        with open(filename, 'w') as f:
            f.write(model)

        p = subprocess.run(['NuSMV', '-keep_single_value_vars', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = p.stdout.decode('UTF-8')

        index = output.index('-- invariant')
        output = output[index:]

        lines = output.splitlines()
        if lines[0].endswith('true'):
            return True
        else:
            return False

    def dumpNumvModel(self, name='main', init=True):
        string = ''

        device_names = sorted(device_name for device_name, device in self.devices.items() if not device.pruned)
        device_names_string = ', '.join(['attack'] + device_names)
        transitions = self.getTransitions()

        for device_name in device_names:
            device = self.devices[device_name]

            module_name = device_name.upper()
            string += 'MODULE {0}({1})\n'.format(module_name, device_names_string)

            # define variables
            string += '  VAR\n'
            for variable_name in sorted(device.getVariableNames()):
                variable = device.getVariable(variable_name)
                if variable.pruned:
                    continue

                variable_range = variable.getPossibleGroupsInNuSMV()
                string += '    {0}: {1};\n'.format(variable_name, variable_range)

            # initial conditions
            string += '  ASSIGN\n'
            if init:
                for variable_name in sorted(device.getVariableNames()):
                    variable = device.getVariable(variable_name)
                    if variable.pruned:
                        continue

                    value = variable.getEquivalentActionCondition(variable.value)
                    string += '    init({0}):= {1};\n'.format(variable_name, value)

                string += '\n'

            # rules
            for variable_name in sorted(device.getVariableNames()):
                variable = device.getVariable(variable_name)
                if variable.pruned:
                    continue

                device_variable = '{0}.{1}'.format(device_name, variable_name)
                rules = transitions[device_variable]

                if len(rules) == 0:
                    continue

                if len(rules) == 1 and rules[0][0] == 'TRUE':
                    string += '    next({0}):= {1};\n'.format(variable_name, rules[0][1])
                else:
                    string += '    next({0}):=\n'.format(variable_name)
                    string += '      case\n'
                    for boolean, value, rule_name in rules:
                        string += '        {0}: {1};\n'.format(boolean, value)
                    if rules[-1][0] != 'TRUE':
                        string += '        {0}: {1};\n'.format('TRUE', variable_name)
                    string += '      esac;\n'

            string += '\n'

        string += 'MODULE {}\n'.format(name)
        string += '  VAR\n'
        for device_name in device_names:
            module_name = device_name.upper()
            string += '    {0}: {1}({2});\n'.format(device_name, module_name, device_names_string)

        string += '\n'
        string += '    attack: boolean;\n'
        string += '\n'
        string += '  ASSIGN init(attack) := FALSE;\n'

        return string

    def grouping(self, policy):
        for rule in self.rules:
            for condition in rule.getConditions():
                for device_name, variable_name, operator, value in condition.getConstraints():
                    if operator == '←':
                        continue
                    elif operator == '≡':
                        # two variables and make their constraints equivalent
                        device = self.devices[device_name]
                        variable = device.getVariable(variable_name)

                        device2_name, variable2_name = value.split('.')
                        device2 = self.devices[device2_name]
                        variable2 = device2.getVariable(variable2_name)

                        constraints = variable.constraints | variable2.constraints
                        variable.constraints = constraints
                        variable2.constraints = constraints

                    else:
                        device = self.devices[device_name]
                        variable = device.getVariable(variable_name)
                        variable.addConstraint(operator, value)

        for device_name, variable_name, operator, value in policy.getConstraints(self):
            if operator == '≡':
                # two variables and make their constraints equivalent
                device = self.devices[device_name]
                variable = device.getVariable(variable_name)

                device2_name, variable2_name = value.split('.')
                device2 = self.devices[device2_name]
                variable2 = device2.getVariable(variable2_name)

                constraints = variable.constraints + variable2.constraints
                variable.constraints = constraints
                variable2.constraints = constraints

            else:
                device = self.devices[device_name]
                variable = device.getVariable(variable_name)
                variable.addConstraint(operator, value)

        for device_name, device in self.devices.items():
            for variable_name, variable in device.variables.items():
                variable.setGrouping(True)

        for rule in self.rules:
            for condition in rule.getConditions():
                condition.toEquivalentCondition(self)

        for condition in policy.getConditions():
            condition.toEquivalentCondition(self)

    def pruning(self, policy):
        graph = networkx.DiGraph()

        for rule in self.rules:
            rule_name = rule.name
            for trigger_variable, action_variable in rule.getDependencies():
                if trigger_variable not in graph:
                    graph.add_node(trigger_variable)

                if action_variable not in graph:
                    graph.add_node(action_variable)

                if not graph.has_edge(trigger_variable, action_variable):
                    graph.add_edge(trigger_variable, action_variable, rules=set())

                graph[trigger_variable][action_variable]['rules'].add(rule_name)

        target_nodes = set(policy.getRelatedVariables(self))
        explored_nodes = set()
        related_rules = set()
        while len(target_nodes) != 0:
            adjacent_nodes = set()
            for trigger_variable, action_variable, data in graph.in_edges_iter(nbunch=target_nodes, data=True):
                adjacent_nodes.add(trigger_variable)
                related_rules |= data['rules']

            explored_nodes |= target_nodes
            target_nodes = adjacent_nodes - explored_nodes

        for device_name, device in self.devices.items():
            for variable_name, variable in device.variables.items():
                if (device_name, variable_name) in explored_nodes:
                    variable.setPruned(False)
                else:
                    variable.setPruned(True)


    def check(self, policy, custom=True, grouping=False, pruning=False):
        if custom:
            for device_name, device in self.devices.items():
                device.addCustomRules(self)

        if grouping:
            self.grouping(policy)

        if pruning:
            self.pruning(policy)

        result = policy.check(self)
        pprint.pprint(result)
        return result



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

    controller.addVulnerableDevice('adafruit')
    # policy = MyInvariantPolicy.InvariantPolicy('adafruit.data != 1 | adafruit.data = 1')
    # policy = MyInvariantPolicy.InvariantPolicy('adafruit.data >= 1 | adafruit.data < 10')
    # policy = MyPrivacyPolicy.PrivacyPolicy(set([('adafruit', 'data')]))
    policy = MyPrivacyPolicy.PrivacyPolicy(set([('androiddevice', 'wifi_connected_network')]))

    controller.check(policy, grouping=True, pruning=True)

