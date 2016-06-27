#!/usr/bin/python3

import channelparser
import random
import json

class NuSMVConverter:
    def __init__(self, directory_path):
        self.channels = channelparser.loadChannelsFromDirectory(directory_path)
        self.variables = set()
        self.rules = []

    def isConvertibleRule(self, trigger_channel, trigger, action_channel, action):
        trigger_name = trigger_channel + ': ' + trigger
        if trigger_name not in self.channels['triggers']:
            return False

        action_name = action_channel + ': ' + action
        if action_name not in self.channels['actions']:
            return False

        return True

    def isUniqueRule(self, trigger_channel, trigger, action_channel, action):
        trigger_name = trigger_channel + ': ' + trigger
        action_name = action_channel + ': ' + action
        if self.channels['triggers'][trigger_name]['input'] or \
                self.channels['actions'][action_name]['input']:
            return True

        if (trigger_name, action_name) in self.rules:
            return False

        return True

    def convertChannelTrigger(self, trigger):
        if 'relationalOperator' in trigger:
            trigger_variable_name = trigger['variable']
            trigger_variable = self.channels['variables'][trigger_variable_name]

            if trigger['value'] == '*':
                if trigger_variable['type'] == 'set':
                    value = random.choice(trigger['valueSet'])
                elif trigger_variable['type'] == 'range':
                    value = str(random.randint(trigger['minValue'], trigger['maxValue']))
            else:
                value = trigger['value']

            return '(%s %s %s)' % (trigger_variable_name, trigger['relationalOperator'], value)

        op = ' ' + trigger['logicalOperator'] + ' '
        return op.join(self.convertChannelTrigger(operand) for operand in trigger['operand'])

    def convertChannelAction(self, action):
        action_variable_name = action['variable']
        action_variable = self.channels['variables'][action_variable_name]

        if action['value'] == '*':
            if action_variable['type'] == 'set':
                return random.choice(action['valueSet'])
            elif action_variable['type'] == 'range':
                return str(random.randint(action['minValue'], action['maxValue']))
        elif action['value'] == '?':
            if action_variable['type'] == 'set':
                return '{' + ', '.join(action['valueSet']) + '}'
            elif action_variable['type'] == 'range':
                return str(action['minValue']) + '..' + str(action['maxValue'])
        elif action['value'] == '!':
            return '!' + action_variable_name
        else:
            return str(action['value'])


    def addRule(self, trigger_channel, trigger, action_channel, action):
        trigger_name = trigger_channel + ': ' + trigger
        action_name = action_channel + ': ' + action
        self.variables.update(self.channels['triggers'][trigger_name]['variables'])
        self.variables.update(self.channels['actions'][action_name]['variables'])
        self.rules.append((trigger_name, action_name))

    def getInitValue(self, variable):
        if variable['type'] == 'set':
            for value in ['none', 'off', 'false']:
                if value in variable['valueSet']:
                    return value
            return random.choice(variable['valueSet'])
        elif variable['type'] == 'boolean':
            return 'FALSE'
        elif variable['type'] == 'range':
            if variable['minValue'] == 0:
                return str(0)
            return str(random.randint(variable['minValue'], variable['maxValue']))

    def dump(self, filename):
        output = 'MODULE main\n'
        output += '\tVAR\n'
        for variable_name in sorted(self.variables):
            variable = self.channels['variables'][variable_name]
            if variable['type'] == 'set':
                variable_range = '{' + ', '.join(variable['valueSet']) + '}'
            elif variable['type'] == 'range':
                variable_range = str(variable['minValue']) + '..' + str(variable['maxValue'])
            elif variable['type'] == 'boolean':
                variable_range = 'boolean'
            output += '\t\t%s: %s;\n' % (variable_name, variable_range)

        output += '\n'
        for idx, (trigger_name, action_name) in enumerate(self.rules, start=1):
            trigger_variables = self.channels['triggers'][trigger_name]['variables']
            action_variables = self.channels['actions'][action_name]['variables']
            variables = set(trigger_variables + action_variables)
            output += '\t\tr%d: process rule%d(%s);\n' % (idx, idx, ', '.join(variables))

        output += '\tASSIGN\n'
        for variable_name in sorted(self.variables):
            variable = self.channels['variables'][variable_name]
            value = self.getInitValue(variable)
            output += '\t\tinit(%s) := %s;\n' % (variable_name, value)

        output += '\n\n'
        for idx, (trigger_name, action_name) in enumerate(self.rules, start=1):
            output += '-- %s\n' % str(rule)

            trigger_variables = self.channels['triggers'][trigger_name]['variables']
            action_variables = self.channels['actions'][action_name]['variables']
            variables = set(trigger_variables + action_variables)
            output += 'MODULE rule%d(%s)\n' % (idx, ', '.join(variables))

            trigger = self.convertChannelTrigger(self.channels['triggers'][trigger_name]['trigger'])
            actions = self.channels['actions'][action_name]['action']
            output += '\tASSIGN\n'
            for action in actions:
                value = self.convertChannelAction(action)
                output += '\t\tnext(%s) :=\n' % action['variable']
                output += '\t\t\tcase\n'
                output += '\t\t\t\t%s: %s;\n' % (trigger, value)
                output += '\t\t\t\tTRUE: %s;\n' % action['variable']
                output += '\t\t\tesac;\n'
            output += '\n'

        with open(filename, 'w') as f:
            f.write(output)



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

            if not converter.isConvertibleRule(trigger_channel, trigger, action_channel, action) or \
                    not converter.isUniqueRule(trigger_channel, trigger, action_channel, action):
                        continue

            converter.addRule(trigger_channel, trigger, action_channel, action)

    converter.dump('test.txt')
