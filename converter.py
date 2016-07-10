#!/usr/bin/python3

import random
import json
import copy
import collections
import networkx

from ifttt import Variable, ExtendSetVariable, Trigger, Action, Rule
from channelparser import loadChannelsFromDirectory
import booleanparser

def check_int(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()

class NuSMVConverter:
    def __init__(self, directory_path):
        self.database = loadChannelsFromDirectory(directory_path)
        self.rules = []
        self.constraint = []
        self.variables = dict()
        self.variable_values = collections.defaultdict(set)
        self.compromised_channels = set()

    def isConvertibleRule(self, trigger_channel, trigger, action_channel, action):
        trigger_key = Trigger.getUniqueName(trigger_channel, trigger)
        action_key = Action.getUniqueName(action_channel, action)

        if trigger_key in self.database['triggers'] and action_key in self.database['actions']:
            return True
        return False

    def addRule(self, trigger_channel, trigger, action_channel, action):
        variables = self.database['variables']

        trigger_key = Trigger.getUniqueName(trigger_channel, trigger)
        trigger_content = self.database['triggers'][trigger_key]
        trigger = Trigger(trigger_channel, trigger, trigger_content, variables)

        action_key = Action.getUniqueName(action_channel, action)
        action_content = self.database['actions'][action_key]
        action = Action(action_channel, action, action_content, variables)

        rule_name = '%s%d' % ('rule', len(self.rules))
        rule = Rule(rule_name, trigger, action)

        for variable_key, valueset in rule.getVariableValuePairs():
            self.variable_values[variable_key].update(valueset)

        self.rules.append(rule)

    def addCompromisedChannel(self, channel):
        self.compromised_channels.add(channel)

    def generateActionTargetValuePairs(self, action):
        for target in action.content:
            variable_name = target['variable']
            variable_key = Variable.getUniqueName(action.channel, variable_name)
            # variable = self.database['variables'][variable_key]
            variable = self.variables[variable_key]

            if target['value'] == '?':
                if variable.old_variable.type == 'set':
                    valueset = target['valueSet']
                elif variable.old_variable.type == 'range':
                    valueset = []
                    i = variable.sorted_valueset.index(target['minValue'])
                    while variable.sorted_valueset[i] != target['maxValue']:
                        valueset.append('d_%s' % variable.sorted_valueset[i])
                        if variable.sorted_valueset[i+1] - variable.sorted_valueset[i] > 1:
                            valueset.append('d_%s_%s' % (variable.sorted_valueset[i], variable.sorted_valueset[i+1]))
                        i += 1
                    valueset.append('d_%s' % variable.sorted_valueset[i])

                value = '{' + ', '.join(valueset) + '}'

            elif target['value'] == '!':
                if variable.type == 'boolean':
                    value = '!' + variable_key
                elif variable.type == 'set':
                    value = 'case\n'
                    value += '\t\t\t\t\t\t\t\t%s = %s: %s;\n' % (variable_key, variable.valueset[0], variable.valueset[1])
                    value += '\t\t\t\t\t\t\t\t%s: %s;\n' % ('TRUE', variable.valueset[0])
                    value += '\t\t\t\t\tesac'
            else:
                if variable.old_variable.type == 'boolean':
                    if target['value'] == 'TRUE':
                        value = 'true'
                    else:
                        value = 'false'
                elif variable.old_variable.type == 'range':
                    value = 'd_' + str(target['value'])
                else:
                    value = str(target['value'])

            yield (variable_key, value)

    def getAllUsedVariableKeys(self):
        variables = set()
        for rule in self.rules:
            variables |= rule.getVariables()
        return variables

    # def getAllCompromisedVariableKeys(self):
    #     variable_keys = set()
    #     for variable_key, variable in self.database['variables'].items():
    #         if variable.channel in self.compromised_channels:
    #             variable_keys.add(variable_key)
    #     return variable_keys
    def addBooleanConstraints(self, boolean):
        self.constraint.append(boolean)

    def convertVariablesToSet(self):
        infix_tokens = booleanparser.tokenParser(self.constraint)
        for variable_key, relational_operator, value in booleanparser.getVariableValuePairs(infix_tokens):
            if check_int(value):
                value = int(value)
            self.variable_values[variable_key].update([value])

        for variable_key, valueset in self.variable_values.items():
            old_variable = self.database['variables'][variable_key]
            self.variables[variable_key] = ExtendSetVariable(old_variable, valueset)

        # self.remaing_rules = []
        G = networkx.DiGraph()
        for rule in self.rules:
            for trigger_variable_key, trigger_valueset in rule.trigger.getPossibleValueSet(self.variables).items():
                for trigger_value in trigger_valueset:
                    trigger_node_name = '_'.join((trigger_variable_key, trigger_value))
                    if trigger_node_name not in G:
                        G.add_node(trigger_node_name)

                    for action_variable_key, action_valueset in rule.action.getPossibleValueSet(self.variables).items():
                        for action_value in action_valueset:
                            action_node_name = '_'.join((action_variable_key, action_value))
                            if action_node_name not in G:
                                G.add_node(action_node_name)

                            if not G.has_edge(trigger_node_name, action_node_name):
                                G.add_edge(trigger_node_name, action_node_name, rules=[])

                            G.edge[trigger_node_name][action_node_name]['rules'].append(rule.name)

        postfix_tokens = booleanparser.infixToPostfix(infix_tokens)
        postfix_tokens.append('!')
        postfix_tokens = booleanparser.expandNotOperator(postfix_tokens)

        endnode_name = set()
        for variable_key, relational_operator, value in booleanparser.getVariableValuePairs(postfix_tokens):
            if check_int(value):
                value = int(value)

            valueset = self.variables[variable_key].getPossibleValueSet(relational_operator, value)
            for value in valueset:
                node_name = '_'.join((variable_key, value))
                endnode_name.add(node_name)

        flag = True
        unexplored_node = endnode_name
        explored_node = set()
        related_rules = set()
        while flag:
            flag = False
            new_unexplored_node = set()
            for node in unexplored_node:
                for predecessor in G.predecessors_iter(node):
                    related_rules.update(G[predecessor][node]['rules'])

                    if predecessor not in explored_node:
                        new_unexplored_node.add(predecessor)
                        flag = True
                explored_node.add(node)

            unexplored_node = new_unexplored_node



        self.all_rules = self.rules
        self.rules = [rule for rule in self.rules if rule.name in related_rules and rule.action.channel not in self.compromised_channels]
        self.graph = G
        self.variable_values = collections.defaultdict(set)

        for rule in self.rules:
            for variable_key, valueset in rule.getVariableValuePairs():
                self.variable_values[variable_key].update(valueset)

        infix_tokens = booleanparser.tokenParser(self.constraint)
        for variable_key, relational_operator, value in booleanparser.getVariableValuePairs(infix_tokens):
            if check_int(value):
                value = int(value)
            self.variable_values[variable_key].update([value])

        for variable_key, valueset in self.variable_values.items():
            old_variable = self.database['variables'][variable_key]
            self.variables[variable_key] = ExtendSetVariable(old_variable, valueset)



    def dump(self, filename):
        with open(filename, 'w') as f:
            f.write(self.dumps())

    def dumps(self):
        self.convertVariablesToSet()
        output = 'MODULE main\n'
        output += '\tVAR\n'

        variable_keys = sorted(self.getAllUsedVariableKeys())
        for variable_key in variable_keys:
            # variable = self.database['variables'][variable_key]
            variable = self.variables[variable_key]
            if variable.type == 'set':
                variable_range = '{' + ', '.join(variable.valueset) + '}'
            elif variable.type == 'range':
                variable_range = str(variable.minvalue) + '..' + str(variable.maxvalue)
            elif variable.type == 'boolean':
                variable_range = 'boolean'
            output += '\t\t%s: %s;\n' % (variable_key, variable_range)
        output += '\n'

        for rule in self.rules:
            if rule.action.channel in self.compromised_channels:
                continue

            action_variables = rule.getExclusiveActionVariables()
            trigger_variables = rule.getTriggerVariables()
            variables = list(trigger_variables) + list(action_variables)
            output += '\t\t%s: process %s(%s);\n' % (rule.name, rule.name, ', '.join(variables))

        output += '\tASSIGN\n'
        for variable_key in variable_keys:
            # variable = self.database['variables'][variable_key]
            variable = self.variables[variable_key]
            value = str(variable.getDefaultValue())
            output += '\t\tinit(%s) := %s;\n' % (variable_key, value)

        infix_tokens = booleanparser.tokenParser(self.constraint)
        testoutput = ''
        for token in infix_tokens:
            if not isinstance(token, tuple):
                testoutput += ' ' + token + ' '
                continue

            variable_key, relational_operator, value = token

            if check_int(value):
                value = int(value)

            valueset = self.variables[variable_key].getPossibleValueSet(relational_operator, value)
            testoutput += '(' + ' | '.join('%s = %s' % (variable_key, value) for value in valueset) + ')'
        output += '\tLTLSPEC G(%s)\n' % testoutput


        output += '\n\n'
        for rule in self.rules:
            if rule.action.channel in self.compromised_channels:
                output += '-- %s\n' % rule
                output += '-- %s\n' % list(rule.trigger.getPossibleValueSet(self.variables).items())
                output += '-- %s\n' % list(rule.action.getPossibleValueSet(self.variables).items())
                continue

            action_variables = rule.getExclusiveActionVariables()
            trigger_variables = rule.getTriggerVariables()
            variables = list(trigger_variables) + list(action_variables)
            output += '-- %s\n' % rule
            output += '-- %s\n' % list(rule.trigger.getPossibleValueSet(self.variables).items())
            output += '-- %s\n' % list(rule.action.getPossibleValueSet(self.variables).items())
            output += 'MODULE %s(%s)\n' % (rule.name, ', '.join(variables))

            trigger_text = rule.trigger.getBooleanFormat(self.variables)
            output += '\tASSIGN\n'
            for (variable_key, value) in self.generateActionTargetValuePairs(rule.action):
                output += '\t\tnext(%s) :=\n' % variable_key
                output += '\t\t\tcase\n'
                output += '\t\t\t\t%s: %s;\n' % (trigger_text, value)
                output += '\t\t\t\tTRUE: %s;\n' % variable_key
                output += '\t\t\tesac;\n'
            output += '\n'

        return output


if __name__ == '__main__':
    converter = NuSMVConverter('./channels/')

    TRIGGER_CHANNEL_IDX = 5
    TRIGGER_IDX = 6
    ACTION_CHANNEL_IDX = 8
    ACTION_IDX = 9

    with open('./coreresults.tsv', mode='r', encoding='UTF-8') as f:
        for line in f:
            line = line.strip()
            columns = line.split('\t')

            trigger_channel = columns[TRIGGER_CHANNEL_IDX]
            trigger = columns[TRIGGER_IDX]
            action_channel = columns[ACTION_CHANNEL_IDX]
            action = columns[ACTION_IDX]

            if converter.isConvertibleRule(trigger_channel, trigger, action_channel, action):
                converter.addRule(trigger_channel, trigger, action_channel, action)

    # converter.addCompromisedChannel('Android Device')

    converter.constraint = 'Android_Device_ringtone_volume >= 9 | Garageio_garage_door_changed = FALSE'

    converter.dump('test2.txt')
