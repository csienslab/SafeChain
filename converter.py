#!/usr/bin/python3

import timeit

from ifttt import VariableType, Trigger, Action, Rule
from channelparser import loadChannelsFromDirectory
import pruner
import grouper

class NuSMVConverter:
    def __init__(self, directory_path):
        self.database = loadChannelsFromDirectory(directory_path)

        self.rules = []
        self.constraint = None
        self.compromised_channels = set()

    def isConvertibleRule(self, trigger_channel_name, trigger_name, action_channel_name, action_name):
        trigger_key = Trigger.getUniqueName(trigger_channel_name, trigger_name)
        action_key = Action.getUniqueName(action_channel_name, action_name)

        if trigger_key in self.database['triggers'] and action_key in self.database['actions']:
            return True
        return False

    def addRule(self, trigger_channel_name, trigger_name, action_channel_name, action_name):
        variables = self.database['variables']

        trigger_key = Trigger.getUniqueName(trigger_channel_name, trigger_name)
        trigger_content = self.database['triggers'][trigger_key]
        trigger = Trigger(trigger_channel_name, trigger_name, trigger_content, variables)

        action_key = Action.getUniqueName(action_channel_name, action_name)
        action_content = self.database['actions'][action_key]
        action = Action(action_channel_name, action_name, action_content, variables)

        rule_name = '%s%d' % ('rule', len(self.rules) + 1)
        rule = Rule(rule_name, trigger, action)
        self.rules.append(rule)

    def addCompromisedChannel(self, channel):
        self.compromised_channels.add(channel)

    def generateActionVariableKeyValuePairs(self, action, variables):
        for variable_key, operator, valueset in action.getVariableKeyOperatorValuePairs(variables):
            if len(valueset) == 1:
                value = str(valueset.pop())
            else:
                value = '{%s}' % ', '.join(str(value) for value in valueset)
            yield (variable_key, value)

    def dump(self, filename, pruning=False, grouping=False):
        with open(filename, 'w') as f:
            f.write(self.dumps(pruning=pruning, grouping=grouping))

    def dumps(self, pruning=False, grouping=False):
        variables = self.database['variables']
        rules = pruner.getUncompromisedRules(self.rules, self.compromised_channels)
        constraint = self.constraint

        if pruning:
            rules = pruner.getRelatedRules(variables, rules, constraint)

        if grouping:
            variables, rules, constraint = grouper.convertToSetVariables(variables, rules, constraint)

        output = 'MODULE main\n'
        output += '\tVAR\n'

        variable_keys = set()
        for rule in rules:
            variable_keys |= rule.getRuleVariables()
        variable_keys = sorted(variable_keys)

        for variable_key in variable_keys:
            variable = variables[variable_key]

            if variable.type == VariableType.BOOLEAN:
                variable_range = 'boolean'
            elif variable.type == VariableType.SET:
                variable_range = '{%s}' % ', '.join(variable.valueset)
            elif variable.type == VariableType.RANGE:
                variable_range = '%d..%d' % (variable.minvalue, variable.maxvalue)
            else:
                raise ValueError('[%s] variable %s with undefined type' % (variable.channel_name, variable.name))

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

        if self.constraint != None:
            output += '\tLTLSPEC G (%s)\n' % constraint

        output += '\n\n'
        for rule in rules:
            output += '-- %s\n' % rule

            action_variables = rule.getExclusiveActionVariables()
            trigger_variables = rule.getTriggerVariables()
            rule_variables = list(trigger_variables) + list(action_variables)
            output += 'MODULE %s(%s)\n' % (rule.name, ', '.join(rule_variables))

            trigger_string = rule.trigger.getBooleanString()
            output += '\tASSIGN\n'
            for variable_key, value in self.generateActionVariableKeyValuePairs(rule.action, variables):
                output += '\t\tnext(%s) :=\n' % variable_key
                output += '\t\t\tcase\n'
                output += '\t\t\t\t%s: %s;\n' % (trigger_string, value)
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

            trigger_channel_name = columns[TRIGGER_CHANNEL_IDX]
            trigger_name = columns[TRIGGER_IDX]
            action_channel_name = columns[ACTION_CHANNEL_IDX]
            action_name = columns[ACTION_IDX]

            if converter.isConvertibleRule(trigger_channel_name, trigger_name, action_channel_name, action_name):
                converter.addRule(trigger_channel_name, trigger_name, action_channel_name, action_name)


    # converter.addCompromisedChannel('Android Device')

    # converter.constraint = 'ANDROID_DEVICE_wifi_status = ON | ANDROID_DEVICE_wifi_status != ON | PHONE_CALL_status = PHONECALL | PHONE_CALL_status != PHONECALL'
    converter.constraint = 'BLINK_1__status = BLINK | BLINK_1__status = NONE'

    converter.dump('test2.txt', pruning=False, grouping=False)

