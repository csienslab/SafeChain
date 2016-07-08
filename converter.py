#!/usr/bin/python3

import random
import json

from ifttt import Variable, Trigger, Action, Rule
from channelparser import loadChannelsFromDirectory

class NuSMVConverter:
    def __init__(self, directory_path):
        self.database = loadChannelsFromDirectory(directory_path)
        self.rules = []
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
        self.rules.append(rule)

    def addCompromisedChannel(self, channel):
        self.compromised_channels.add(channel)

    def generateActionTargetValuePairs(self, action):
        for target in action.content:
            variable_name = target['variable']
            variable_key = Variable.getUniqueName(action.channel, variable_name)
            variable = self.database['variables'][variable_key]

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

    def dump(self, filename):
        with open(filename, 'w') as f:
            f.write(self.dumps())

    def dumps(self):
        output = 'MODULE main\n'
        output += '\tVAR\n'

        variable_keys = sorted(self.getAllUsedVariableKeys())
        for variable_key in variable_keys:
            variable = self.database['variables'][variable_key]
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
            variable = self.database['variables'][variable_key]
            value = str(variable.getDefaultValue())
            output += '\t\tinit(%s) := %s;\n' % (variable_key, value)

        output += '\n\n'
        for rule in self.rules:
            if rule.action.channel in self.compromised_channels:
                output += '-- %s\n' % rule
                continue

            action_variables = rule.getExclusiveActionVariables()
            trigger_variables = rule.getTriggerVariables()
            variables = list(trigger_variables) + list(action_variables)
            output += '-- %s\n' % rule
            output += 'MODULE %s(%s)\n' % (rule.name, ', '.join(variables))

            trigger_text = rule.trigger.getBooleanFormat()
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

    converter.addCompromisedChannel('Android Device')

    converter.dump('test2.txt')
