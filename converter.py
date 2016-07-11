#!/usr/bin/python3

import random
import json
import copy
import collections
import networkx
import matplotlib.pyplot as plt

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
        self.constraint = None
        self.compromised_channels = set()

    def isConvertibleRule(self, trigger_channel, trigger, action_channel, action):
        trigger_key = Trigger.getUniqueName(trigger_channel, trigger)
        action_key = Action.getUniqueName(action_channel, action)

        if trigger_key in self.database['triggers'] and action_key in self.database['actions']:
            return True
        return False

    def getVariableValues(self, rules):
        variable_values = collections.defaultdict(set)

        for rule in rules:
            for variable_key, valueset in rule.getVariableValuePairs():
                variable_values[variable_key].update(valueset)

        if self.constraint != None:
            infix_tokens = booleanparser.tokenParser(self.constraint)
            for variable_key, relational_operator, value in booleanparser.getVariableValuePairs(infix_tokens):
                if check_int(value):
                    value = int(value)
                variable_values[variable_key].update([value])

        return variable_values

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
        self.rules.append(rule)

    def addCompromisedChannel(self, channel):
        self.compromised_channels.add(channel)

    def generateActionTargetValuePairs(self, action, variables):
        for target in action.content:
            variable_name = target['variable']
            variable_key = Variable.getUniqueName(action.channel, variable_name)
            variable = variables[variable_key]

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

    def generateActionTargetValuePairs_test(self, action, variables):
        for target in action.content:
            variable_name = target['variable']
            variable_key = Variable.getUniqueName(action.channel, variable_name)
            variable = variables[variable_key]

            if target['value'] == '?':
                if variable.type == 'set':
                    value = '{' + ', '.join(target['valueSet']) + '}'
                elif variable.type == 'range':
                    value = str(target['minValue']) + '..' + str(target['maxValue'])
            elif target['value'] == '!':
                if variable.type == 'boolean':
                    value = '!' + variable_key
                elif variable.type == 'set':
                    value = 'case\n'
                    value += '\t\t\t\t\t\t\t\t%s = %s: %s;\n' % (variable_key, variable.valueset[0], variable.valueset[1])
                    value += '\t\t\t\t\t\t\t\t%s: %s;\n' % ('TRUE', variable.valueset[0])
                    value += '\t\t\t\t\tesac'
            else:
                value = str(target['value'])

            yield (variable_key, value)

    # def getAllCompromisedVariableKeys(self):
    #     variable_keys = set()
    #     for variable_key, variable in self.database['variables'].items():
    #         if variable.channel in self.compromised_channels:
    #             variable_keys.add(variable_key)
    #     return variable_keys

    # def addBooleanConstraints(self, boolean):
    #     self.constraint.append(boolean)

    def convertVariablesToSet(self, rules):
        variables = dict()
        variable_values = self.getVariableValues(rules)

        for variable_key, valueset in variable_values.items():
            old_variable = self.database['variables'][variable_key]
            variables[variable_key] = ExtendSetVariable(old_variable, valueset)

        return variables

    def getGraphNodeName(variable_key, value):
        return '_'.join((variable_key, value))

    def getRelatedRules(self, rules):
        if self.constraint == None:
            return rules

        variables = self.convertVariablesToSet(rules)

        G = networkx.DiGraph()
        for rule in rules:
            for trigger_variable_key, trigger_valueset in rule.trigger.getPossibleValueSet(variables).items():
                for trigger_value in trigger_valueset:
                    trigger_node_name = NuSMVConverter.getGraphNodeName(trigger_variable_key, trigger_value)
                    if trigger_node_name not in G:
                        G.add_node(trigger_node_name)




                    for action_variable_key, action_valueset in rule.action.getPossibleValueSet(variables).items():
                        for action_value in action_valueset:
                            action_node_name = NuSMVConverter.getGraphNodeName(action_variable_key, action_value)
                            if action_node_name not in G:
                                G.add_node(action_node_name)

                            if not G.has_edge(trigger_node_name, action_node_name):
                                G.add_edge(trigger_node_name, action_node_name, rules=[])

                            G.edge[trigger_node_name][action_node_name]['rules'].append(rule.name)





        infix_tokens = booleanparser.tokenParser(self.constraint)
        postfix_tokens = booleanparser.infixToPostfix(infix_tokens)
        postfix_tokens.append('!')
        postfix_tokens = booleanparser.expandNotOperator(postfix_tokens)

        target_node = set()
        for variable_key, relational_operator, value in booleanparser.getVariableValuePairs(postfix_tokens):
            if check_int(value):
                value = int(value)

            valueset = variables[variable_key].getPossibleValueSet(relational_operator, value)
            for value in valueset:
                node_name = NuSMVConverter.getGraphNodeName(variable_key, value)
                target_node.add(node_name)

        unexplored_node = target_node
        explored_node = set()
        related_rules = set()

        while len(unexplored_node) != 0:
            new_unexplored_node = set()
            for node in unexplored_node:
                if node not in G:
                    continue

                for predecessor in G.predecessors_iter(node):
                    related_rules.update(G[predecessor][node]['rules'])

                    if predecessor not in explored_node:
                        new_unexplored_node.add(predecessor)

                explored_node.add(node)

            unexplored_node = new_unexplored_node

        related_rules = [rule for rule in rules if rule.name in related_rules]
        return related_rules

    def getUncompromisedRules(self, rules):
        return [rule for rule in rules if rule.action.channel not in self.compromised_channels]

    def dump(self, filename):
        with open(filename, 'w') as f:
            f.write(self.dumps())

    def dumps(self):
        rules = self.getUncompromisedRules(self.rules)
        rules = self.getRelatedRules(rules)
        variables = self.convertVariablesToSet(rules)
        generateActionTargetValuePairs = self.generateActionTargetValuePairs
        setflag = True
        # rules = self.rules
        # variables = self.database['variables']
        # generateActionTargetValuePairs = self.generateActionTargetValuePairs_test
        # setflag = False

        output = 'MODULE main\n'
        output += '\tVAR\n'

        variable_keys = sorted(variables.keys())
        for variable_key in variable_keys:
            variable = variables[variable_key]

            if variable.type == 'set':
                variable_range = '{' + ', '.join(variable.valueset) + '}'
            elif variable.type == 'range':
                variable_range = str(variable.minvalue) + '..' + str(variable.maxvalue)
            elif variable.type == 'boolean':
                variable_range = 'boolean'

            output += '\t\t%s: %s;\n' % (variable_key, variable_range)
        output += '\n'

        for rule in rules:
            action_variables = rule.getExclusiveActionVariables()
            trigger_variables = rule.getTriggerVariables()
            rule_variables = list(trigger_variables) + list(action_variables)
            output += '\t\t%s: process %s(%s);\n' % (rule.name, rule.name, ', '.join(rule_variables))

        output += '\tASSIGN\n'
        for variable_key in variable_keys:
            variable = variables[variable_key]
            value = str(variable.getDefaultValue())
            output += '\t\tinit(%s) := %s;\n' % (variable_key, value)

        if setflag:
            infix_tokens = booleanparser.tokenParser(self.constraint)
            testoutput = ''
            for token in infix_tokens:
                if not isinstance(token, tuple):
                    testoutput += ' ' + token + ' '
                    continue

                variable_key, relational_operator, value = token

                if check_int(value):
                    value = int(value)

                valueset = variables[variable_key].getPossibleValueSet(relational_operator, value)
                testoutput += '(' + ' | '.join('%s = %s' % (variable_key, value) for value in valueset) + ')'
            output += '\tLTLSPEC G(%s)\n' % testoutput


        output += '\n\n'
        for rule in rules:
            action_variables = rule.getExclusiveActionVariables()
            trigger_variables = rule.getTriggerVariables()
            rule_variables = list(trigger_variables) + list(action_variables)
            output += '-- %s\n' % rule
            # output += '-- %s\n' % list(rule.trigger.getPossibleValueSet(variables).items())
            # output += '-- %s\n' % list(rule.action.getPossibleValueSet(variables).items())
            output += 'MODULE %s(%s)\n' % (rule.name, ', '.join(rule_variables))

            trigger_text = rule.trigger.getBooleanFormat(variables)
            output += '\tASSIGN\n'
            for (variable_key, value) in generateActionTargetValuePairs(rule.action, variables):
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

    converter.constraint = 'Garageio_garage_door_opened = FALSE | ( Android_Device_WiFi_turned_on = TRUE & Android_Device_WiFi_network = 7 )'

    converter.dump('test2.txt')
