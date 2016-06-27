#!/usr/bin/python3

import channelparser
import random
import json

class NuSMVConverter:
    def __init__(self, directory_path):
        self.channels, self.channel_variables = channelparser.loadChannelsFromDirectory(directory_path)
        self.variables = {}
        self.rules = []

    def isConvertibleRule(self, trigger_channel, trigger, action_channel, action):
        if trigger_channel not in self.channels or trigger not in self.channels[trigger_channel]['triggers']:
            return False

        if action_channel not in self.channels or action not in self.channels[action_channel]['actions']:
            return False

        return True

    def isUniqueRule(self, trigger_channel, trigger, action_channel, action):
        if '*' in json.dumps(self.channels[trigger_channel]['triggers'][trigger]):
            return True

        if '*' in json.dumps(self.channels[action_channel]['actions'][action]):
            return True

        if (trigger_channel, trigger, action_channel, action) in self.rules:
            return False

        return True

    def extractActionVariables(action):
        return set(x['variable'] for x in action)

    def extractTriggerVariables(trigger):
        if 'relationalOperator' in trigger:
            return set([trigger['variable']])

        variables = set()
        for op in trigger['operand']:
            variables = variables | NuSMVConverter.extractTriggerVariables(op)

        return variables

    def convertChannelTrigger(self, trigger):
        if 'relationalOperator' in trigger:
            if trigger['value'] == '*':
                if self.channel_variables[trigger['variable']]['type'] == 'set':
                    value = random.choice(trigger['valueSet'])
                elif self.channel_variables[trigger['variable']]['type'] == 'range':
                    value = str(random.randint(trigger['minValue'], trigger['maxValue']))
            else:
                value = trigger['value']

            return '%s %s %s' % (trigger['variable'], trigger['relationalOperator'], value)
        elif 'logicalOperator' in trigger:
            op = ' ' + trigger['logicalOperator'] + ' '
            return op.join(self.convertChannelTrigger(operand) for operand in trigger['operand'])

    def convertChannelAction(self, action):
        if action['value'] == '*':
            if self.channel_variables[action['variable']]['type'] == 'set':
                return random.choice(action['valueSet'])
            elif self.channel_variables[action['variable']]['type'] == 'range':
                return str(random.randint(action['minValue'], action['maxValue']))
        elif action['value'] == '?':
            if self.channel_variables[action['variable']]['type'] == 'set':
                return '{' + ', '.join(action['valueSet']) + '}'
            elif self.channel_variables[action['variable']]['type'] == 'range':
                return str(action['minValue']) + '..' + str(action['maxValue'])
        else:
            return action['value']


    def addRule(self, trigger_channel, trigger, action_channel, action):
        if trigger_channel not in self.channels or trigger not in self.channels[trigger_channel]['triggers']:
            raise ValueError('[%s] (%s) unsupported trigger' % (trigger_channel, trigger))
        if action_channel not in self.channels or action not in self.channels[action_channel]['actions']:
            raise ValueError('[%s] (%s) unsupported action' % (action_channel, action))

        variables = NuSMVConverter.extractActionVariables(self.channels[action_channel]['actions'][action]) | NuSMVConverter.extractTriggerVariables(self.channels[trigger_channel]['triggers'][trigger])
        for variable in variables:
            self.variables[variable] = self.channel_variables[variable]

        self.rules.append((trigger_channel, trigger, action_channel, action))

    def getInitValue(variable):
        if variable['type'] == 'set':
            for value in ['none', 'off', 'false']:
                if value in variable['value']:
                    return value

            return random.choice(variable['value'])
        elif variable['type'] == 'range':
            if variable['minValue'] == 0:
                return str(0)
            return str(random.randint(variable['minValue'], variable['maxValue']))

    def dump(self, filename):
        output = 'MODULE main\n\tVAR\n'
        for variable_name in sorted(self.variables):
            variable = self.variables[variable_name]
            if variable['type'] == 'set':
                output += '\t\t' + variable_name + ': {' + ', '.join(variable['value']) + '};\n'
            elif variable['type'] == 'range':
                output += '\t\t' + variable_name + ': ' + str(variable['minValue']) + '..' + str(variable['maxValue']) + ';\n'

        output += '\n'
        for idx, rule in enumerate(self.rules, start=1):
            output += '\t\tr' + str(idx) + ': process rule' + str(idx) + '('
            variables = NuSMVConverter.extractTriggerVariables(self.channels[rule[0]]['triggers'][rule[1]]) | NuSMVConverter.extractActionVariables(self.channels[rule[2]]['actions'][rule[3]])
            output += ', '.join(variables)
            output += ');\n'

        output += '\tASSIGN\n'
        for variable_name in sorted(self.variables):
            output += '\t\tinit(' + variable_name + ') := '
            variable = self.variables[variable_name]
            output += NuSMVConverter.getInitValue(variable)
            output += ';\n'

        output += '\n\n'
        for idx, rule in enumerate(self.rules, start=1):
            output += '-- ' + str(rule) + '\n'
            output += 'MODULE rule' + str(idx) + '('
            variables = NuSMVConverter.extractTriggerVariables(self.channels[rule[0]]['triggers'][rule[1]]) | NuSMVConverter.extractActionVariables(self.channels[rule[2]]['actions'][rule[3]])
            output += ', '.join(variables)
            output += ')\n\tASSIGN\n'
            trigger = self.convertChannelTrigger(self.channels[rule[0]]['triggers'][rule[1]])
            actions = self.channels[rule[2]]['actions'][rule[3]]
            for action in actions:
                output += '\t\tnext(' + action['variable'] +') :=\n'
                output += '\t\t\tcase\n'
                value = str(self.convertChannelAction(action))
                output += '\t\t\t\t' + trigger + ': ' + value + ';\n'
                output += '\t\t\t\tTRUE: ' + action['variable'] + ';\n'
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
