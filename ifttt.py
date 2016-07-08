#!/usr/bin/python3

import random
import json

class Variable:
    # TODO 
    # use Enum to represent type
    def __init__(self, channel, name, content):
        self.checkInitErrors(channel, name, content)

        self.channel = channel
        self.name = name
        self.type = content['type']
        if self.type == 'set':
            self.valueset = content['valueSet']
        elif self.type == 'range':
            self.minvalue = content['minValue']
            self.maxvalue = content['maxValue']

    # def __hash__(self):
    #     return hash(self.name)

    # def __eq__(self, other):
    #     return self.name == other.name

    def checkInitErrors(self, channel, name, content):
        if 'type' not in content:
            raise ValueError('[%s] variable %s with undefined type' % (channel, name))

        if content['type'] not in ['boolean', 'set', 'range']:
            raise ValueError('[%s] variable %s with unsupported type %s' % (channel, name, content['type']))

        if content['type'] == 'set':
            if 'valueSet' not in content:
                raise ValueError('[%s] variable %s with undefined valueSet' % (channel, name))
            elif len(content['valueSet']) == 0:
                raise ValueError('[%s] variable %s with empty set' % (channel, name))

        if content['type'] == 'range':
            if 'minValue' not in content:
                raise ValueError('[%s] variable %s with undefined minValue' % (channel, name))
            elif 'maxValue' not in content:
                raise ValueError('[%s] variable %s with undefined maxValue' % (channel, name))

    def checkCmpErrors(self, trigger_name, content):
        if self.type == 'boolean':
            if content['value'] != 'FALSE' and content['value'] != 'TRUE':
                raise ValueError('[%s] trigger %s with boolean variable %s ill-assignment' % (self.channel, trigger_name, self.name))
            elif content['relationalOperator'] != '=' and content['relationalOperator'] != '!=':
                raise ValueError('[%s] trigger %s with boolean variable %s illegal relational operator' % (self.channel, trigger_name, self.name))
            else:
                return

        elif self.type == 'set':
            if content['relationalOperator'] != '=' and content['relationalOperator'] != '!=':
                raise ValueError('[%s] trigger %s with set variable %s illegal relational operator' % (self.channel, trigger_name, self.name))
            elif content['value'] == '*' and set(content['valueSet']) <= set(self.valueset):
                return
            elif content['value'] != '*' and content['value'] in self.valueset:
                return
            else:
                raise ValueError('[%s] trigger %s with set variable %s illegal valueSet' % (self.channel, trigger_name, self.name))

        elif self.type == 'range':
            if content['value'] == '*' and \
               (content['minValue'] >= self.minvalue and content['minValue'] <= self.maxvalue) and \
               (content['maxValue'] >= self.minvalue and content['maxValue'] <= self.maxvalue):
                   return
            elif content['value'] != '*' and isinstance(content['value'], int) and \
                 (content['value'] >= self.minvalue and content['value'] <= self.maxvalue):
                     return
            else:
                raise ValueError('[%s] trigger %s with range variable %s illegal minValue and maxValue' % (self.channel, trigger_name, self.name))

    def checkAssignErrors(self, action_name, content):
        if self.type == 'boolean':
            if content['value'] == '!' or content['value'] == 'FALSE' or content['value'] == 'TRUE':
                return
            else:
                raise ValueError('[%s] action %s with boolean variable %s ill-assignment' % (self.channel, action_name, self.name))

        elif self.type == 'set':
            if (content['value'] == '*' or content['value'] == '?') and set(content['valueSet']) <= set(self.valueset):
                return
            elif content['value'] == '!' and len(self.valueset) == 2:
                return
            elif (content['value'] != '*' and content['value'] != '?' and content['value'] != '!') and content['value'] in self.valueset:
                return
            else:
                raise ValueError('[%s] action %s with set variable %s ill-assignment' % (self.channel, action_name, self.name))

        elif self.type == 'range':
            if (content['value'] == '*' or content['value'] == '?') and \
               (content['minValue'] >= self.minvalue and content['minValue'] <= self.maxvalue) and \
               (content['maxValue'] >= self.minvalue and content['maxValue'] <= self.maxvalue):
                   return
            elif (content['value'] != '*' and content['value'] != '?') and isinstance(content['value'], int) and\
                 (content['value'] >= self.minvalue and content['value'] <= self.maxvalue):
                     return
            else:
                raise ValueError('[%s] action %s with range variable %s ill-assignment' % (self.channel, action_name, self.name))

    def getRandomValue(self, content):
        if self.type == 'set':
            return random.choice(content['valueSet'])
        elif self.type == 'range':
            return random.randint(content['minValue'], content['maxValue'])
        else:
            return random.choice(['TRUE', 'FALSE'])

    def getDefaultValue(self):
        if self.type == 'set':
            for value in self.valueset:
                if value in ['none', 'off', 'false']:
                    return value
            return random.choice(self.valueset)
        elif self.type == 'range':
            if self.minvalue == 0:
                return 0
            return random.randint(variable['minValue'], variable['maxValue'])
        else:
            return 'FALSE'

    def getUniqueName(channel, name):
        return name

class Trigger:
    def checkErrors(channel, name, content, variables):
        if 'relationalOperator' in content:
            variable_name = content['variable']
            variable_key = Variable.getUniqueName(channel, variable_name)
            if variable_key not in variables:
                raise ValueError('[%s] trigger %s with variable %s undefined' % (channel, name, variable_name))

            variable = variables[variable_key]
            variable.checkCmpErrors(name, content)

        elif 'logicalOperator' in content:
            if content['logicalOperator'] not in ['&', '|']:
                raise ValueError('[%s] trigger %s with unsupported logical operator %s' % (channel, name, content['logicalOperator']))

            for operand in content['operand']:
                Trigger.checkErrors(channel, name, operand, variables)
        else:
            raise ValueError('[%s] trigger %s is not defined well' % (channel, name))

    def __init__(self, channel, name, content, variables):
        self.channel = channel
        self.name = name
        self.content = self.setUserInput(channel, content, variables)

    def __str__(self):
        return str((self.channel, self.name))

    def setUserInput(self, channel, content, variables):
        if 'relationalOperator' in content:
            if content['value'] == '*':
                variable_name = content['variable']
                variable_key = Variable.getUniqueName(channel, variable_name)
                variable = variables[variable_key]

                content['value'] = variable.getRandomValue(content)
                content.pop('valueSet', None)
                content.pop('minValue', None)
                content.pop('maxValue', None)
            return content

        content['operand'] = [self.setUserInput(channel, operand, variables) for operand in content['operand']]
        return content

    def getVariables(self, content=None):
        if content is None:
            content = self.content

        if 'relationalOperator' in content:
            variable_key = Variable.getUniqueName(self.channel, content['variable'])
            return set([variable_key])

        variables = set()
        for operand in content['operand']:
            variables |= self.getVariables(operand)
        return variables

    def getBooleanFormat(self, content=None):
        if content is None:
            content = self.content

        if 'relationalOperator' in content:
            return '%s %s %s' % (content['variable'], content['relationalOperator'], content['value'])

        op = ' ' + content['logicalOperator'] + ' '
        return '(' + op.join(self.getBooleanFormat(operand) for operand in content['operand']) + ')'

    def getUniqueName(channel, name):
        return ': '.join([channel, name])



class Action:
    def checkErrors(channel, name, content, variables):
        for action in content:
            variable_name = action['variable']
            variable_key = Variable.getUniqueName(channel, variable_name)
            if variable_key not in variables:
                raise ValueError('[%s] action %s with variable %s undefined' % (channel, name, variable_name))

            variable = variables[variable_key]
            variable.checkAssignErrors(name, action)

    def __init__(self, channel, name, content, variables):
        self.channel = channel
        self.name = name
        self.content = self.setUserInput(channel, content, variables)

    def __str__(self):
        return str((self.channel, self.name))

    def setUserInput(self, channel, content, variables):
        for action in content:
            if action['value'] != '*':
                continue

            variable_name = action['variable']
            variable_key = Variable.getUniqueName(channel, variable_name)
            variable = variables[variable_key]

            action['value'] = variable.getRandomValue(action)
            action.pop('valueSet', None)
            action.pop('minValue', None)
            action.pop('maxValue', None)
        return content

    def getVariables(self):
        variables = set()
        for action in self.content:
            variable_key = Variable.getUniqueName(self.channel, action['variable'])
            variables.add(variable_key)
        return variables

    def getUniqueName(channel, name):
        return ': '.join([channel, name])


class Rule:
    def __init__(self, name, trigger, action):
        self.name = name
        self.trigger = trigger
        self.action = action

        self.rule_string = json.dumps(trigger.content) + json.dumps(action.content)

    def __str__(self):
        return '%s %s -> %s' % (self.name, self.trigger, self.action)

    def getTriggerVariables(self):
        return self.trigger.getVariables()

    def getActionVariables(self):
        return self.action.getVariables()

    def getVariables(self):
        return self.getTriggerVariables() | self.getActionVariables()

    def getExclusiveActionVariables(self):
        return self.getActionVariables() - self.getTriggerVariables()

