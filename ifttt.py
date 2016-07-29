#!/usr/bin/python3

import random
import copy
import collections
import enum
import re

class VariableType(enum.Enum):
    BOOLEAN = 0
    SET = 1
    RANGE = 2

class Variable:
    def checkErrors(channel_name, variable_name, variable_content):
        if 'type' not in variable_content:
            raise ValueError('[%s] variable %s with undefined type' % (channel_name, variable_name))

        if variable_content['type'] not in ('boolean', 'set', 'range'):
            raise ValueError('[%s] variable %s with unsupported type %s' % (channel_name, variable_name, variable_content['type']))

        if variable_content['type'] == 'set':
            if 'valueSet' not in variable_content:
                raise ValueError('[%s] variable %s with undefined valueSet' % (channel_name, variable_name))
            elif len(variable_content['valueSet']) == 0:
                raise ValueError('[%s] variable %s with empty set' % (channel_name, variable_name))

        elif variable_content['type'] == 'range':
            if 'minValue' not in variable_content:
                raise ValueError('[%s] variable %s with undefined minValue' % (channel_name, variable_name))
            elif 'maxValue' not in variable_content:
                raise ValueError('[%s] variable %s with undefined maxValue' % (channel_name, variable_name))

    def __init__(self, channel_name, name, content):
        self.channel_name = channel_name
        self.name = name

        if content['type'] == 'boolean':
            self.type = VariableType.BOOLEAN
        elif content['type'] == 'set':
            self.type = VariableType.SET
            self.valueset = tuple(content['valueSet'])
        elif content['type'] == 'range':
            self.type = VariableType.RANGE
            self.minvalue = content['minValue']
            self.maxvalue = content['maxValue']
        else:
            raise ValueError('[%s] trigger %s is not defined well' % (channel_name, name))

    def checkComparisonErrors(self, trigger_name, trigger_content):
        if self.type == VariableType.BOOLEAN:
            if trigger_content['value'] not in ('TRUE', 'FALSE', '*'):
                raise ValueError('[%s] trigger %s with boolean variable %s ill-assignment' % (self.channel_name, trigger_name, self.name))
            elif trigger_content['relationalOperator'] not in ('=', '!='):
                raise ValueError('[%s] trigger %s with boolean variable %s illegal relational operator' % (self.channel_name, trigger_name, self.name))
            else:
                return

        elif self.type == VariableType.SET:
            if trigger_content['relationalOperator'] not in ('=', '!='):
                raise ValueError('[%s] trigger %s with set variable %s illegal relational operator' % (self.channel_name, trigger_name, self.name))
            elif trigger_content['value'] == '*' or trigger_content['value'] in self.valueset:
                return
            else:
                raise ValueError('[%s] trigger %s with set variable %s illegal valueSet' % (self.channel_name, trigger_name, self.name))

        elif self.type == VariableType.RANGE:
            if trigger_content['value'] == '*':
                return
            elif isinstance(trigger_content['value'], int) and trigger_content['value'] >= self.minvalue and trigger_content['value'] <= self.maxvalue:
                return
            else:
                raise ValueError('[%s] trigger %s with range variable %s illegal minValue and maxValue' % (self.channel_name, trigger_name, self.name))

        else:
            raise ValueError('[%s] trigger %s is not defined well' % (self.channel_name, trigger_name))

    def checkAssignmentErrors(self, action_name, action_content):
        if self.type == VariableType.BOOLEAN:
            if action_content['value'] in ('TRUE', 'FALSE', '!', '*'):
                return
            else:
                raise ValueError('[%s] action %s with boolean variable %s ill-assignment' % (self.channel_name, action_name, self.name))

        elif self.type == VariableType.SET:
            if action_content['value'] in ('*', '?'):
                return
            elif action_content['value'] == '!' and len(self.valueset) == 2:
                return
            elif action_content['value'] not in ('*', '?', '!') and action_content['value'] in self.valueset:
                return
            else:
                raise ValueError('[%s] action %s with set variable %s ill-assignment' % (self.channel_name, action_name, self.name))

        elif self.type == VariableType.RANGE:
            if action_content['value'] in ('*', '?'):
                return
            elif isinstance(action_content['value'], int) and action_content['value'] >= self.minvalue and action_content['value'] <= self.maxvalue:
                return
            else:
                raise ValueError('[%s] action %s with range variable %s ill-assignment' % (self.channel_name, action_name, self.name))

        else:
            raise ValueError('[%s] action %s is not defined well' % (self.channel_name, action_name))

    def getPossibleValues(self):
        if self.type == VariableType.BOOLEAN:
            return set(['TRUE', 'FALSE'])
        elif self.type == VariableType.SET:
            return set(self.valueset)
        elif self.type == VariableType.RANGE:
            return set(range(self.minvalue, self.maxvalue + 1))
        else:
            raise ValueError('[%s] variable %s is not defined well' % (self.channel_name, self.name))

    def getRandomValue(self):
        if self.type == VariableType.BOOLEAN:
            return random.choice(('TRUE', 'FALSE'))
        elif self.type == VariableType.SET:
            return random.choice(self.valueset)
        elif self.type == VariableType.RANGE:
            return random.randint(self.minvalue, self.maxvalue)
        else:
            raise ValueError('[%s] variable %s is not defined well' % (self.channel_name, self.name))

    def getDefaultValue(self):
        if self.type == VariableType.BOOLEAN:
            return 'FALSE'
        elif self.type == VariableType.SET:
            # if none, off, false exist, choose them first
            valueset = tuple(set(self.valueset) & set(('none', 'off', 'false', 'NONE', 'OFF', 'FALSE', 'NO')))
            if len(valueset) == 0:
                valueset = self.valueset
            return random.choice(valueset)
        elif self.type == VariableType.RANGE:
            if self.minvalue == 0:
                return 0
            return random.randint(self.minvalue, self.maxvalue)
        else:
            raise ValueError('[%s] variable %s is not defined well' % (self.channel_name, self.name))

    def getUniqueName(channel_name, variable_name):
        name = '_'.join((channel_name.upper(), variable_name))
        name = re.sub('[^A-Za-z0-9_]', '_', name)
        return name


class Trigger:
    def checkErrors(channel_name, trigger_name, trigger_content, variables):
        if 'relationalOperator' in trigger_content:
            variable_name = trigger_content['variable']
            variable_key = Variable.getUniqueName(channel_name, variable_name)
            if variable_key not in variables:
                raise ValueError('[%s] trigger %s with variable %s undefined' % (channel_name, trigger_name, variable_name))

            variable = variables[variable_key]
            variable.checkComparisonErrors(trigger_name, trigger_content)

        elif 'logicalOperator' in trigger_content:
            if trigger_content['logicalOperator'] not in ('&', '|'):
                raise ValueError('[%s] trigger %s with unsupported logical operator %s' % (channel_name, trigger_name, trigger_content['logicalOperator']))

            for operand in trigger_content['operand']:
                Trigger.checkErrors(channel_name, trigger_name, operand, variables)

        else:
            raise ValueError('[%s] trigger %s is not defined well' % (channel_name, trigger_name))

    def __init__(self, channel_name, name, content, variables):
        self.channel_name = channel_name
        self.name = name

        self.content = copy.deepcopy(content)
        self.setUserInput(variables)

    def __str__(self):
        return str((self.channel_name, self.name))

    def setUserInput(self, variables, content=None):
        """
        for each variable with value *, generate a random value for it
        """
        if content == None:
            content = self.content

        if 'relationalOperator' in content:
            if content['value'] == '*':
                variable_name = content['variable']
                variable_key = Variable.getUniqueName(self.channel_name, variable_name)
                variable = variables[variable_key]

                content['value'] = variable.getRandomValue()

        elif 'logicalOperator' in content:
            for operand in content['operand']:
                self.setUserInput(variables, operand)

        else:
            raise ValueError('[%s] trigger %s is not defined well' % (self.channel_name, self.name))

    def getVariableKeys(self, content=None):
        """
        get all variable keys associated with this trigger
        return set([variable_key1, variable_key2, ...])
        """
        if content == None:
            content = self.content

        if 'relationalOperator' in content:
            variable_name = content['variable']
            variable_key = Variable.getUniqueName(self.channel_name, variable_name)
            return set([variable_key])

        elif 'logicalOperator' in content:
            variable_keys = set()
            for operand in content['operand']:
                variable_keys |= self.getVariableKeys(operand)
            return variable_keys

        else:
            raise ValueError('[%s] trigger %s is not defined well' % (self.channel_name, self.name))

    def getVariableKeyOperatorValuePairs(self, variables, content=None):
        """
        get all variable keys and their associated values in this trigger
        return [(variable_key1, operator, set([value1, value2, ...])), ...]
        """
        if content == None:
            content = self.content

        if 'relationalOperator' in content:
            variable_name = content['variable']
            variable_key = Variable.getUniqueName(self.channel_name, variable_name)
            valueset = set([content['value']])

            return [(variable_key, content['relationalOperator'], valueset)]

        elif 'logicalOperator' in content:
            variable_key_operator_value_pairs = []
            for operand in content['operand']:
                pairs = self.getVariableKeyOperatorValuePairs(variables, operand)
                variable_key_operator_value_pairs += pairs

            return variable_key_operator_value_pairs

        else:
            raise ValueError('[%s] trigger %s is not defined well' % (self.channel_name, self.name))

    def getBooleanString(self, content=None):
        """
        get the boolean string for this trigger used in NuSMV
        return str
        """
        if content == None:
            content = self.content

        if 'relationalOperator' in content:
            variable_name = content['variable']
            variable_key = Variable.getUniqueName(self.channel_name, variable_name)

            return '%s %s %s' % (variable_key, content['relationalOperator'], content['value'])

        elif 'logicalOperator' in content:
            operator = ' ' + content['logicalOperator'] + ' '
            boolean_string = operator.join(self.getBooleanString(operand) for operand in content['operand'])

            return '( %s )' % boolean_string

        else:
            raise ValueError('[%s] trigger %s is not defined well' % (self.channel_name, self.name))

    def getUniqueName(channel_name, name):
        return ': '.join((channel_name, name))

class Action:
    def checkErrors(channel_name, action_name, action_content, variables):
        for action in action_content:
            variable_name = action['variable']
            variable_key = Variable.getUniqueName(channel_name, variable_name)
            if variable_key not in variables:
                raise ValueError('[%s] action %s with variable %s undefined' % (channel_name, action_name, variable_name))

            variable = variables[variable_key]
            variable.checkAssignmentErrors(action_name, action)

    def __init__(self, channel_name, name, content, variables):
        self.channel_name = channel_name
        self.name = name

        self.content = copy.deepcopy(content)
        self.setUserInput(variables)

    def __str__(self):
        return str((self.channel_name, self.name))

    def setUserInput(self, variables):
        """
        for each variable with value *, generate a random value for it
        """
        for action in self.content:
            if action['value'] == '*':
                variable_name = action['variable']
                variable_key = Variable.getUniqueName(self.channel_name, variable_name)
                variable = variables[variable_key]

                action['value'] = variable.getRandomValue()

    def getVariableKeys(self):
        """
        get all variable keys associated with this action
        return set([variable_key1, variable_key2, ...])
        """
        variable_keys = set()

        for action in self.content:
            variable_name = action['variable']
            variable_key = Variable.getUniqueName(self.channel_name, variable_name)
            variable_keys.add(variable_key)

        return variable_keys

    def getVariableKeyOperatorValuePairs(self, variables):
        """
        get the sequential pairs of variable keys and their associated values in this action
        return [(variable_key1, '=', value1), (variable_key2, '=', value2), ...]
        """
        variable_key_operator_value_pairs = []

        for action in self.content:
            variable_name = action['variable']
            variable_key = Variable.getUniqueName(self.channel_name, variable_name)
            variable = variables[variable_key]

            if action['value'] in ('?', '!'):
                valueset = variable.getPossibleValues()
            else:
                valueset = set([action['value']])

            variable_key_operator_value_pairs.append((variable_key, '=', valueset))

        return variable_key_operator_value_pairs

    def getUniqueName(channel_name, name):
        return ': '.join((channel_name, name))

class Rule:
    def __init__(self, name, trigger, action):
        self.name = name
        self.trigger = trigger
        self.action = action

    def __str__(self):
        return '%s %s -> %s' % (self.name, self.trigger, self.action)

    def getTriggerVariables(self):
        return self.trigger.getVariableKeys()

    def getActionVariables(self):
        return self.action.getVariableKeys()

    def getRuleVariables(self):
        return self.getTriggerVariables() | self.getActionVariables()

    def getExclusiveActionVariables(self):
        return self.getActionVariables() - self.getTriggerVariables()

    def getVariableKeyOperatorValuePairs(self, variables):
        return self.trigger.getVariableKeyOperatorValuePairs(variables) + self.action.getVariableKeyOperatorValuePairs(variables)
