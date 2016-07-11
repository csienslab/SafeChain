#!/usr/bin/python3

import random
import json
import copy
import collections

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

    def getApproriateValueSet(self, relational_operator, value):
        return (relational_operator, [value])

    def getPossibleValues(self, content):
        if self.type == 'set':
            if content['value'] == '!':
                return set(self.valueset)
            else:
                return set(content['valueSet'])
        elif self.type == 'range':
            return set(range(content['minValue'], content['maxValue'] + 1))
        else:
            return set(['TRUE', 'FALSE'])

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

class ExtendSetVariable(Variable):
    def __init__(self, old_variable, valueset):
        if old_variable.type == 'boolean':
            variable_valueset = ['true', 'false']
        elif old_variable.type == 'range':
            variable_valueset = []
            sorted_valueset = sorted(valueset)
            self.sorted_valueset = sorted_valueset

            if old_variable.minvalue not in valueset:
                if sorted_valueset[0] - old_variable.minvalue == 1:
                    variable_valueset.append('d_%s' % old_variable.minvalue)
                else:
                    variable_valueset.append('d_%s_%s' % (old_variable.minvalue, sorted_valueset[0]))


            i = 0;
            while i + 1 < len(sorted_valueset):
                variable_valueset.append('d_%s' % sorted_valueset[i])
                if sorted_valueset[i+1] - sorted_valueset[i] > 1:
                    variable_valueset.append('d_%s_%s' % (sorted_valueset[i], sorted_valueset[i+1]))
                i += 1

            variable_valueset.append('d_%s' % sorted_valueset[i])
            if old_variable.maxvalue not in valueset:
                if old_variable.maxvalue - sorted_valueset[-1] == 1:
                    variable_valueset.append('d_%s' % old_variable.maxvalue)
                else:
                    variable_valueset.append('d_%s_%s' % (sorted_valueset[-1], old_variable.maxvalue))
        else:
            variable_valueset = old_variable.valueset

        content = {'type': 'set', 'valueSet': variable_valueset}
        Variable.__init__(self, old_variable.channel, old_variable.name, content)
        self.old_variable = old_variable

    def getApproriateValueSet(self, relational_operator, value):
        if self.old_variable.type == 'boolean':
            if value == 'TRUE':
                return (relational_operator, ['true'])
            else:
                return (relational_operator, ['false'])

        if self.old_variable.type == 'set':
            return (relational_operator, [value])

        # range
        if relational_operator == '=' or relational_operator == '!=':
            return (relational_operator, ['d_' + str(value)])

        # <, <=, >, >=
        if relational_operator == '>' or relational_operator == '>=':
            valueset = []
            i = self.sorted_valueset.index(value)
            if relational_operator == '>=':
                valueset.append('d_%s' % self.sorted_valueset[i])

            while i+1 < len(self.sorted_valueset):
                if self.sorted_valueset[i+1] - self.sorted_valueset[i] > 1:
                    valueset.append('d_%s_%s' % (self.sorted_valueset[i], self.sorted_valueset[i+1]))
                valueset.append('d_%s' % self.sorted_valueset[i+1])
                i += 1

            if self.old_variable.maxvalue not in self.sorted_valueset:
                valueset.append('d_%s_%s' % (self.sorted_valueset[-1], self.old_variable.maxvalue))
        else:
            valueset = []
            i = self.sorted_valueset.index(value)
            if relational_operator == '<=':
                valueset.append('d_%s' % self.sorted_valueset[i])

            while i-1 > 0:
                if self.sorted_valueset[i] - self.sorted_valueset[i-1] > 1:
                    valueset.append('d_%s_%s' % (self.sorted_valueset[i-1], self.sorted_valueset[i]))
                valueset.append('d_%s' % self.sorted_valueset[i-1])
                i -= 1

            if self.old_variable.minvalue not in self.sorted_valueset:
                valueset.append('d_%s_%s' % (self.old_variable.minvalue, self.sorted_valueset[0]))

        return ('=', valueset)

    def getPossibleValueSet(self, relational_operator, value):
        if self.old_variable.type == 'boolean':
            if value == 'TRUE':
                value = 'true'
            else:
                value = 'false'

        if relational_operator == '=':
            if isinstance(value, int):
                value = 'd_%s' % str(value)
            return set([value])
        elif relational_operator == '!=':
            if isinstance(value, int):
                value = 'd_%s' % str(value)
            return set(self.valueset) - set([value])
        else:
            # range <, <=, >, >=
            if relational_operator == '>' or relational_operator == '>=':
                valueset = set()
                i = self.sorted_valueset.index(value)
                if relational_operator == '>=':
                    valueset.add('d_%s' % self.sorted_valueset[i])

                while i+1 < len(self.sorted_valueset):
                    if self.sorted_valueset[i+1] - self.sorted_valueset[i] > 1:
                        valueset.add('d_%s_%s' % (self.sorted_valueset[i], self.sorted_valueset[i+1]))
                    valueset.add('d_%s' % self.sorted_valueset[i+1])
                    i += 1

                if self.old_variable.maxvalue not in self.sorted_valueset:
                    valueset.add('d_%s_%s' % (self.sorted_valueset[-1], self.old_variable.maxvalue))
            else:
                valueset = set()
                i = self.sorted_valueset.index(value)
                if relational_operator == '<=':
                    valueset.add('d_%s' % self.sorted_valueset[i])

                while i-1 >= 0:
                    if self.sorted_valueset[i] - self.sorted_valueset[i-1] > 1:
                        valueset.add('d_%s_%s' % (self.sorted_valueset[i-1], self.sorted_valueset[i]))
                    valueset.add('d_%s' % self.sorted_valueset[i-1])
                    i -= 1

                if self.old_variable.minvalue not in self.sorted_valueset:
                    valueset.add('d_%s_%s' % (self.old_variable.minvalue, self.sorted_valueset[0]))

            return valueset


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
        content = copy.deepcopy(content)

        self.channel = channel
        self.name = name
        self.content = self.genUserInput(channel, content, variables)

    def __str__(self):
        return str((self.channel, self.name))

    # TODO
    # self probably not needed
    def genUserInput(self, channel, content, variables):
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

        content['operand'] = [self.genUserInput(channel, operand, variables) for operand in content['operand']]
        return content

    def getVariableValuePairs(self, content=None):
        if content == None:
            content = self.content

        if 'relationalOperator' in content:
            variable_name = content['variable']
            variable_key = Variable.getUniqueName(self.channel, variable_name)
            valueset = set([content['value']])

            return [(variable_key, valueset)]

        variable_value_pairs = []
        for operand in content['operand']:
            variable_value_pairs += self.getVariableValuePairs(operand)
        return variable_value_pairs

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

    def getBooleanFormat(self, variables, content=None):
        if content is None:
            content = self.content

        if 'relationalOperator' in content:
            variable_name = content['variable']
            variable_key = Variable.getUniqueName(self.channel, variable_name)
            variable = variables[variable_key]
            relational_operator, valueset = variable.getApproriateValueSet(content['relationalOperator'], content['value'])
            if len(valueset) == 1:
                return '%s %s %s' % (variable_key, relational_operator, valueset[0])
            else:
                return ' | '.join('%s %s %s' % (variable_key, relational_operator, value) for value in valueset)

        op = ' ' + content['logicalOperator'] + ' '
        return '(' + op.join(self.getBooleanFormat(variables, operand) for operand in content['operand']) + ')'

    def getPossibleValueSet(self, variables, content=None):
        if content is None:
            content = self.content
            self.variable_possible_valueset = collections.defaultdict(set)

        if 'relationalOperator' in content:
            variable_name = content['variable']
            variable_key = Variable.getUniqueName(self.channel, variable_name)
            variable = variables[variable_key]
            valueset = variable.getPossibleValueSet(content['relationalOperator'], content['value'])
            self.variable_possible_valueset[variable_key].update(valueset)
            return self.variable_possible_valueset

        for operand in content['operand']:
            self.getPossibleValueSet(variables, operand)
        return self.variable_possible_valueset

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
        content = copy.deepcopy(content)

        self.channel = channel
        self.name = name
        self.content = self.genUserInput(channel, content, variables)

    def __str__(self):
        return str((self.channel, self.name))

    def genUserInput(self, channel, content, variables):
        for action in content:
            if action['value'] == '*':
                variable_name = action['variable']
                variable_key = Variable.getUniqueName(channel, variable_name)
                variable = variables[variable_key]

                action['value'] = variable.getRandomValue(action)
                action.pop('valueSet', None)
                action.pop('minValue', None)
                action.pop('maxValue', None)
        return content

    def getVariableValuePairs(self, variables):
        variable_value_pairs = []
        for action in self.content:
            variable_name = action['variable']
            variable_key = Variable.getUniqueName(self.channel, variable_name)
            variable = variables[variable_key]

            if action['value'] == '?' or action['value'] == '!':
                valueset = variable.getPossibleValues(action)
            else:
                valueset = set([action['value']])

            variable_value_pairs.append((variable_key, valueset))

        return variable_value_pairs

    def getVariables(self):
        variables = set()
        for action in self.content:
            variable_key = Variable.getUniqueName(self.channel, action['variable'])
            variables.add(variable_key)
        return variables

    def getPossibleValueSet(self, variables):
        variable_possible_valueset = collections.defaultdict(set)
        for target in self.content:
            variable_name = target['variable']
            variable_key = Variable.getUniqueName(self.channel, variable_name)
            # variable = self.database['variables'][variable_key]
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
            elif target['value'] == '!':
                if variable.old_variable.type == 'boolean':
                    valueset = ['true', 'false']
                elif variable.type == 'set':
                    valueset = variable.valueset
            else:
                if variable.old_variable.type == 'boolean':
                    if target['value'] == 'TRUE':
                        valueset = ['true']
                    else:
                        valueset = ['false']
                elif variable.old_variable.type == 'range':
                    valueset = ['d_' + str(target['value'])]
                else:
                    valueset = [target['value']]

            variable_possible_valueset[variable_key].update(valueset)

        return variable_possible_valueset

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

    def getVariableValuePairs(self):
        return self.trigger.getVariableValuePairs() + self.action.getVariableValuePairs()

    def getTriggerVariables(self):
        return self.trigger.getVariables()

    def getActionVariables(self):
        return self.action.getVariables()

    def getVariables(self):
        return self.getTriggerVariables() | self.getActionVariables()

    def getExclusiveActionVariables(self):
        return self.getActionVariables() - self.getTriggerVariables()

