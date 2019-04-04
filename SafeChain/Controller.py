#!/usr/bin/env python3

# TODO
# rules attached to variables and channels
# divide using set
# combine boolean into set
# class sensor and actuator if without rules all possible
# use str.join instead of +
# [80%] assign variable with variable using same constraints
# using subrule and rule for multicondition
# incorporate array

import pickle
import collections
import random
import re
import networkx
import subprocess
import datetime
import pprint
import time
import os
import tempfile

import SafeChain.Trigger as MyTrigger
import SafeChain.Action as MyAction
import SafeChain.Rule as MyRule

class Controller:
    def __init__(self, database):
        self.database = database

        self.channels = dict()
        self.rules = list()
        self.vulnerables = set()

        self.channel_variables = set()

    def getFeasibleChannels(self):
        return self.database.items()

    def addChannel(self, channel):
        channel_name = channel.name
        self.channels[channel_name] = channel

    def addVulnerableChannel(self, channel_name):
        if channel_name not in self.channels:
            return False

        channel = self.channels[channel_name]
        for variable_name in channel.getVariableNames():
            self.vulnerables.add((channel_name, variable_name))

        return True

    def addVulnerableChannelVariable(self, channel_name, variable_name):
        if channel_name not in self.channels:
            return False

        channel = self.channels[channel_name]
        if variable_name not in channel.getVariableNames():
            return False

        self.vulnerables.add((channel_name, variable_name))
        return True

    def getFeasibleInputs(self, input_definitions, parameters, forbid=set()):
        index = len(parameters)
        if index >= len(input_definitions):
            return None

        input_definition = input_definitions[index]
        input_type = input_definition['type']

        if input_type == 'channel':
            channel_type = set(input_definition['channel'])
            feasible_inputs = set(channel_name for channel_name, channel in self.channels.items() if channel.channel_name in channel_type)
        elif input_type == 'variable':
            channel_name = input_definition['channel'].format(*parameters)
            channel = self.channels[channel_name]
            feasible_inputs = channel.getVariableNames()
        elif input_type == 'value':
            channel_name = input_definition['channel'].format(*parameters)
            variable_name = input_definition['variable'].format(*parameters)

            channel = self.channels[channel_name]
            variable = channel.getVariable(variable_name)
            feasible_inputs = variable.getPossibleValues() - forbid
        elif input_type == 'set':
            feasible_inputs = set(input_definition['setValue'])
        else:
            raise TypeError('Unknown input type')

        exceptions = set(input_definition['exceptions']) if 'exceptions' in input_definition else set()
        return feasible_inputs - exceptions

    def getFeasibleInputsForTrigger(self, channel_name, trigger_name, forbid=set()):
        input_definitions = self.database[channel_name]['triggers'][trigger_name]['input']
        parameters = list()

        feasible_inputs = self.getFeasibleInputs(input_definitions, parameters)
        while feasible_inputs != None:
            feasible_input = random.choice(tuple(feasible_inputs))
            parameters.append(feasible_input)
            feasible_inputs = self.getFeasibleInputs(input_definitions, parameters, forbid)

        return tuple(parameters)

    def getFeasibleInputsForAction(self, channel_name, action_name, forbid=set()):
        input_definitions = self.database[channel_name]['actions'][action_name]['input']
        parameters = list()

        feasible_inputs = self.getFeasibleInputs(input_definitions, parameters, forbid)
        while feasible_inputs != None:
            feasible_input = random.choice(tuple(feasible_inputs))
            parameters.append(feasible_input)
            feasible_inputs = self.getFeasibleInputs(input_definitions, parameters, forbid)

        return tuple(parameters)

    def addRule(self, rule_name,
                trigger_channel_name, trigger_name, trigger_inputs,
                action_channel_name, action_name, action_inputs):
        trigger_definition = self.database[trigger_channel_name]['triggers'][trigger_name]
        trigger = MyTrigger.Trigger(rule_name, trigger_channel_name, trigger_definition, trigger_name, trigger_inputs)
        action_definition = self.database[action_channel_name]['actions'][action_name]
        action = MyAction.Action(rule_name, action_channel_name, action_definition, action_name, action_inputs)

        #  print(trigger_name, trigger_inputs, action_name, action_inputs)
        #  print(list(trigger.getConditions())[0].tupple)
        rule = MyRule.Rule(rule_name, trigger, action)
        self.rules.append(rule)

        for channel_name, variable_name in rule.getVariables():
            self.channel_variables.add((channel_name, variable_name))

    def addCustomRule(self, rule_name,
                      trigger_channel_name, trigger_name, trigger_definition, trigger_inputs,
                      action_channel_name, action_name, action_definition, action_inputs):
        trigger = MyTrigger.Trigger(rule_name, trigger_channel_name, trigger_definition, trigger_name, trigger_inputs)
        action = MyAction.Action(rule_name, action_channel_name, action_definition, action_name, action_inputs)

        rule = MyRule.Rule(rule_name, trigger, action)
        self.rules.append(rule)

        for channel_name, variable_name in rule.getVariables():
            self.channel_variables.add((channel_name, variable_name))

    def getChannel(self, channel_name):
        if channel_name not in self.channels:
            return None

        return self.channels[channel_name]

    def getTransitions(self):
        transitions = collections.defaultdict(list)

        # add rule
        for rule in self.rules:
            for boolean, channel_variable, value in rule.getTransitions():
                channel_name, variable_name = channel_variable.split('.')
                channel = self.channels[channel_name]
                variable = channel.getVariable(variable_name)
                if variable.pruned:
                    continue

                transitions[channel_variable].append((boolean, value, rule.name))

        # add reset value
        for channel_name, channel in self.channels.items():
            for variable_name, variable in channel.variables.items():
                if variable.pruned:
                    continue
                if variable.reset_value == None:
                    continue

                value = variable.getEquivalentActionCondition(variable.reset_value)
                channel_variable = '{0}.{1}'.format(channel_name, variable_name)
                if channel_variable not in transitions:
                    # because no rules
                    continue

                transitions[channel_variable].append(('TRUE', str(value), 'RESET'))

        # add attack
        for channel_name, variable_name in self.vulnerables:
            channel = self.channels[channel_name]
            variable = channel.getVariable(variable_name)
            if variable.pruned:
                continue

            channel_variable = '{0}.{1}'.format(channel_name, variable_name)
            if channel_variable not in transitions:
                # because no rules
                continue

            variable_range = variable.getPossibleGroupsInNuSMV()
            if variable_range == 'boolean':
                variable_range = '{TRUE, FALSE}'
            transitions[channel_variable].insert(0, ('next(attack)', variable_range, 'ATTACK'))

        return transitions

    def checkRuleSatisfied(self, state, rule_condition):
        string_list = list()

        channel_names = list()
        for channel_name, channel in self.channels.items():
            if channel.pruned:
                continue

            variable_names = [variable_name
                              for variable_name in channel.getVariableNames()
                              if (channel_name, variable_name) in self.channel_variables
                              and not channel.getVariable(variable_name).pruned]

            if len(variable_names) == 0:
                continue

            channel_names.append(channel_name)
        channel_names = sorted(channel_names)
        channel_names_string = ', '.join(['attack'] + channel_names)

        for channel_name in channel_names:
            channel = self.channels[channel_name]

            variable_names = [variable_name
                              for variable_name in channel.getVariableNames()
                              if (channel_name, variable_name) in self.channel_variables
                              and not channel.getVariable(variable_name).pruned]

            if len(variable_names) == 0:
                continue

            module_name = channel_name.upper()
            string_list.append('MODULE {0}({1})'.format(module_name, channel_names_string))

            # define variables
            variable_names = sorted(variable_names)
            string_list.append('  FROZENVAR')
            for variable_name in variable_names:
                variable = channel.getVariable(variable_name)
                variable_range = variable.getPossibleGroupsInNuSMV()
                string_list.append('    {0}: {1};'.format(variable_name, variable_range))

            # initial conditions
            string_list.append('  ASSIGN')
            for variable_name in variable_names:
                variable = channel.getVariable(variable_name)
                value = state['{0}.{1}'.format(channel_name, variable_name)]
                string_list.append('    init({0}):= {1};'.format(variable_name, value))
            string_list.append('')

        string_list.append('MODULE main')
        string_list.append('  VAR')
        for channel_name in channel_names:
            module_name = channel_name.upper()
            string_list.append('    {0}: {1}({2});'.format(channel_name, module_name, channel_names_string))

        string_list.append('')
        string_list.append('    attack: boolean;')
        string_list.append('')
        string_list.append('  ASSIGN attack := FALSE;')
        string_list.append('')
        string_list.append('  INVARSPEC {};'.format(rule_condition))

        model = '\n'.join(string_list)

        _, filename = tempfile.mkstemp()
        with open(filename, 'w') as f:
            f.write(model)

        p = subprocess.run(['NuSMV', '-keep_single_value_vars', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = p.stdout.decode('UTF-8')
        os.remove(filename)

        index = output.index('-- invariant')
        output = output[index:]

        lines = output.splitlines()
        if lines[0].endswith('true'):
            return True
        else:
            return False

    def dumpNumvModel(self, name='main', init=True):
        string_list = []

        channel_names = list()
        for channel_name, channel in self.channels.items():
            if channel.pruned:
                continue

            variable_names = [variable_name
                              for variable_name in channel.getVariableNames()
                              if (channel_name, variable_name) in self.channel_variables
                              and not channel.getVariable(variable_name).pruned]

            if len(variable_names) == 0:
                continue

            channel_names.append(channel_name)
        channel_names = sorted(channel_names)

        channel_names_string = ', '.join(['attack'] + channel_names)
        transitions = self.getTransitions()

        for channel_name in channel_names:
            channel = self.channels[channel_name]

            variable_names = [variable_name
                              for variable_name in channel.getVariableNames()
                              if (channel_name, variable_name) in self.channel_variables
                              and not channel.getVariable(variable_name).pruned]

            if len(variable_names) == 0:
                continue

            module_name = channel_name.upper()
            string_list.append('MODULE {0}({1})'.format(module_name, channel_names_string))

            # define variables
            variable_names = sorted(variable_names)
            string_list.append('  VAR')
            for variable_name in variable_names:
                variable = channel.getVariable(variable_name)
                variable_range = variable.getPossibleGroupsInNuSMV()
                string_list.append('    {0}: {1};'.format(variable_name, variable_range))

            # initial conditions
            string_list.append('  ASSIGN')
            if init:
                for variable_name in variable_names:
                    variable = channel.getVariable(variable_name)
                    value = variable.getEquivalentActionCondition(variable.value)
                    string_list.append('    init({0}):= {1};'.format(variable_name, value))

                string_list.append('')

            # rules
            for variable_name in variable_names:
                variable = channel.getVariable(variable_name)
                channel_variable = '{0}.{1}'.format(channel_name, variable_name)
                rules = transitions[channel_variable]

                if len(rules) == 0:
                    continue

                if len(rules) == 1 and rules[0][0] == 'TRUE':
                    string_list.append('    next({0}):= {1};'.format(variable_name, rules[0][1]))
                else:
                    string_list.append('    next({0}):='.format(variable_name))
                    string_list.append('      case')
                    for boolean, value, rule_name in rules:
                        string_list.append('        {0}: {1};'.format(boolean, value))
                    if rules[-1][0] != 'TRUE':
                        string_list.append('        {0}: {1};'.format('TRUE', variable_name))
                    string_list.append('      esac;')

            string_list.append('')

        string_list.append('MODULE {}'.format(name))
        string_list.append('  VAR')
        for channel_name in channel_names:
            module_name = channel_name.upper()
            string_list.append('    {0}: {1}({2});'.format(channel_name, module_name, channel_names_string))

        string_list.append('')
        string_list.append('    attack: boolean;')
        string_list.append('')
        string_list.append('  ASSIGN init(attack) := FALSE;')

        return '\n'.join(string_list)

    def grouping(self, policy):
        self.ungrouping(policy)
        for rule in self.rules:
            for condition in rule.getConditions():
                for channel_name, variable_name, operator, value in condition.getConstraints():
                    if operator == '←':
                        continue
                    elif operator == '≡':
                        # two variables and make their constraints equivalent
                        channel = self.channels[channel_name]
                        variable = channel.getVariable(variable_name)

                        channel2_name, variable2_name = value.split('.')
                        channel2 = self.channels[channel2_name]
                        variable2 = channel2.getVariable(variable2_name)

                        constraints = variable.constraints | variable2.constraints
                        variable.constraints = constraints
                        variable2.constraints = constraints

                    else:
                        channel = self.channels[channel_name]
                        variable = channel.getVariable(variable_name)
                        variable.addConstraint(operator, value)

        for channel_name, variable_name, operator, value in policy.getConstraints(self):
            if operator == '≡':
                # two variables and make their constraints equivalent
                channel = self.channels[channel_name]
                variable = channel.getVariable(variable_name)

                channel2_name, variable2_name = value.split('.')
                channel2 = self.channels[channel2_name]
                variable2 = channel2.getVariable(variable2_name)

                constraints = variable.constraints + variable2.constraints
                variable.constraints = constraints
                variable2.constraints = constraints

            else:
                channel = self.channels[channel_name]
                variable = channel.getVariable(variable_name)
                variable.addConstraint(operator, value)

        for channel_name, channel in self.channels.items():
            for variable_name, variable in channel.variables.items():
                variable.setGrouping(True)

        for rule in self.rules:
            for condition in rule.getConditions():
                condition.toEquivalentCondition(self)

        for condition in policy.getConditions():
            condition.toEquivalentCondition(self)

    def ungrouping(self, policy):
        for channel_name, channel in self.channels.items():
            for variable_name, variable in channel.variables.items():
                variable.setGrouping(False)

        for rule in self.rules:
            for condition in rule.getConditions():
                condition.toOriginal()

        for condition in policy.getConditions():
            condition.toOriginal()

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

        target_nodes = set(policy.getRelatedVariables(self, graph))
        explored_nodes = set()
        related_rules = set()
        while len(target_nodes) != 0:
            adjacent_nodes = set()
            for trigger_variable, action_variable, data in graph.in_edges_iter(nbunch=target_nodes, data=True):
                adjacent_nodes.add(trigger_variable)
                related_rules |= data['rules']

            explored_nodes |= target_nodes
            target_nodes = adjacent_nodes - explored_nodes

        for channel_name, channel in self.channels.items():
            for variable_name, variable in channel.variables.items():
                if (channel_name, variable_name) in explored_nodes:
                    variable.setPruned(False)
                else:
                    variable.setPruned(True)

    def unpruning(self, policy):
        for channel_name, channel in self.channels.items():
            for variable_name, variable in channel.variables.items():
                variable.setPruned(False)

    def check(self, policy, custom=True, grouping=False, pruning=False, timeout=1800, bmc=False):
        if custom:
            for channel_name, channel in self.channels.items():
                channel.addCustomRules(self)

        if grouping == True:
            grouping_start = time.perf_counter()
            self.grouping(policy)
            grouping_time = time.perf_counter() - grouping_start
        elif grouping == False:
            self.ungrouping(policy)
            grouping_time = 0
        else:
            grouping_time = 0

        if pruning == True:
            pruning_start = time.perf_counter()
            self.pruning(policy)
            pruning_time = time.perf_counter() - pruning_start
        elif pruning == False:
            self.unpruning(policy)
            pruning_time = 0
        else:
            pruning_time = 0

        total_start = time.perf_counter()
        filename, result, checking_time = policy.check(self, timeout, bmc)
        total_time = time.perf_counter() - total_start

        return filename, result, grouping_time, pruning_time, total_time - checking_time, checking_time
