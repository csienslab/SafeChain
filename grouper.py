#!/usr/bin/python3

import collections

from ifttt import Variable, VariableType, Trigger, Action, Rule
import booleanparser

class ExtendedSetVariable(Variable):
    def __init__(self, original_variable, valueset):
        if original_variable.type == VariableType.BOOLEAN:
            variable_valueset = ['YES', 'NO']
        elif original_variable.type == VariableType.SET:
            # TODO use valueset instead?
            # No! Because it will miss something like "NONE"
            variable_valueset = list(original_variable.valueset)
        elif original_variable.type == VariableType.RANGE:
            variable_valueset = []

            valueset.add(original_variable.minvalue)
            valueset.add(original_variable.maxvalue)
            sorted_values = sorted(valueset)

            for current_value, next_value in zip(sorted_values, sorted_values[1:]):
                variable_valueset.append('d_%d' % current_value)
                if next_value - current_value != 1:
                    variable_valueset.append('d_%d_%d' % (current_value, next_value))
            variable_valueset.append('d_%d' % sorted_values[-1])

            self.sorted_values = sorted_values
        else:
            raise ValueError('[%s] trigger %s is not defined well' % (original_variable.channel_name, original_variable.name))

        content = {'type': 'set', 'valueSet': variable_valueset}
        Variable.__init__(self, original_variable.channel_name, original_variable.name, content)

        self.original_type = original_variable.type

    def getElementName(self, value):
        if value in ('?', '!'):
            return value

        if self.original_type == VariableType.BOOLEAN:
            if value == 'TRUE':
                return 'YES'
            elif value == 'FALSE':
                return 'NO'
            else:
                raise ValueError('[%s] variable %s is not defined well' % (self.channel_name, self.name))

        elif self.original_type == VariableType.SET:
            return value

        elif self.original_type == VariableType.RANGE:
            if not isinstance(value, int):
                raise ValueError('[%s] variable %s is not defined well' % (self.channel_name, self.name))

            return 'd_%d' % value

        else:
            raise ValueError('[%s] variable %s is not defined well' % (self.channel_name, self.name))


    def getEquivalentValueSet(self, relational_operator, value):
        if value == '?':
            return self.valueset

        if self.original_type in (VariableType.BOOLEAN, VariableType.SET):
            value = self.getElementName(value)

            if relational_operator == '=':
                return set([value])
            elif relational_operator == '!=':
                return set(self.valueset) - set([value])
            else:
                raise ValueError('[%s] variable %s with incompatible relational operator' % (self.channel_name, self.name))

        elif self.original_type == VariableType.RANGE:
            number = value
            value = self.getElementName(number)

            if relational_operator == '=':
                return set([value])
            elif relational_operator == '!=':
                return set(self.valueset) - set([value])
            elif relational_operator in ('<', '<=', '>', '>='):
                variable_valueset = []

                if '<' in relational_operator:
                    sorted_values = list(reversed(self.sorted_values))
                else:
                    sorted_values = self.sorted_values

                i = sorted_values.index(number)
                if '=' in relational_operator:
                    variable_valueset.append(self.getElementName(sorted_values[i]))

                for current_value, next_value in zip(sorted_values[i:], sorted_values[i+1:]):
                    if '<' in relational_operator:
                        if current_value - next_value != 1:
                            variable_valueset.append('d_%d_%d' % (next_value, current_value))
                    else:
                        if next_value - current_value != 1:
                            variable_valueset.append('d_%d_%d' % (current_value, next_value))
                    variable_valueset.append(self.getElementName(next_value))

                return set(variable_valueset)
            else:
                raise ValueError('[%s] variable %s with incompatible relational operator' % (self.channel_name, self.name))

        else:
            raise ValueError('[%s] variable %s is not defined well' % (self.channel_name, self.name))

    def getTrueValueSet(self, relational_operator, valueset):
        if self.type == VariableType.SET:
            if relational_operator == '=':
                return valueset
            elif relational_operator == '!=':
                return set(self.valueset) - valueset
            else:
                raise ValueError('[%s] variable %s with incompatible relational operator' % (self.channel_name, self.name))

        else:
            raise ValueError('[%s] variable %s cannot get the true value set' % (self.channel_name, self.name))



class ExtendedTrigger(Trigger):
    def convertToSetVariables(channel_name, content, variables):
        """
        """
        if 'relationalOperator' in content:
            variable_name = content['variable']
            variable_key = Variable.getUniqueName(channel_name, variable_name)
            variable = variables[variable_key]

            if content['relationalOperator'] in ('=', '!='):
                value = variable.getElementName(content['value'])
                return {'relationalOperator': content['relationalOperator'], 'value': value, 'variable': variable_name}

            elif content['relationalOperator'] in ('<', '<=', '>', '>='):
                operands = []

                valueset = variable.getEquivalentValueSet(content['relationalOperator'], content['value'])
                for value in valueset:
                    operand = {'relationalOperator': '=', 'value': value, 'variable': variable_name}
                    operands.append(operand)

                return {'logicalOperator': '|', 'operand': operands}

            else:
                raise ValueError('[%s] variable %s with incompatible relational operator' % (self.channel_name, self.name))

        elif 'logicalOperator' in content:
            operands = []
            for operand in content['operand']:
                operand = ExtendedTrigger.convertToSetVariables(channel_name, operand, variables)
                operands.append(operand)

            return {'logicalOperator': content['logicalOperator'], 'operand': operands}

        else:
            raise ValueError('[%s] trigger %s is not defined well' % (self.channel_name, self.name))

    def __init__(self, original_trigger, variables):
        content = ExtendedTrigger.convertToSetVariables(original_trigger.channel_name, original_trigger.content, variables)
        Trigger.__init__(self, original_trigger.channel_name, original_trigger.name, content, variables)


class ExtendedAction(Action):
    def convertToSetVariables(channel_name, content, variables):
        """
        """
        actions = []

        for action in content:
            variable_name = action['variable']
            variable_key = Variable.getUniqueName(channel_name, variable_name)
            variable = variables[variable_key]

            value = variable.getElementName(action['value'])
            actions.append({'variable': variable_name, 'value': value})

        return actions

    def __init__(self, original_action, variables):
        content = ExtendedAction.convertToSetVariables(original_action.channel_name, original_action.content, variables)
        Action.__init__(self, original_action.channel_name, original_action.name, content, variables)


def check_int(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()


def getVariableKeyValuePairs(variables, rules, constraint=None):
    variable_key_value_pairs = collections.defaultdict(set)

    for rule in rules:
        for variable_key, operator, valueset in rule.getVariableKeyOperatorValuePairs(variables):
            variable_key_value_pairs[variable_key].update(valueset)

    if constraint != None:
        infix_tokens = booleanparser.tokenParser(constraint)
        for variable_key, relational_operator, value in booleanparser.getVariableKeyOperatorValuePairs(infix_tokens):
            if check_int(value):
                value = int(value)
            variable_key_value_pairs[variable_key].add(value)

    return variable_key_value_pairs

def convertConstraintToSetVariables(constraint, variables):
    if constraint == None:
        return None

    set_constraint = []

    infix_tokens = booleanparser.tokenParser(constraint)
    for token in infix_tokens:
        if isinstance(token, tuple):
            variable_key, relational_operator, value = token
            variable = variables[variable_key]

            if check_int(value):
                value = int(value)

            if relational_operator in ('=', '!='):
                value = variable.getElementName(value)
                set_constraint.append('%s %s %s' % (variable_key, relational_operator, value))

            elif relational_operator in ('<', '<=', '>', '>='):
                valueset = variable.getEquivalentValueSet(relational_operator, value)

                set_constraint.append('(')
                for value in valueset:
                    set_constraint.append('%s %s %s' % (variable_key, '=', value))
                    set_constraint.append('|')
                set_constraint.pop()
                set_constraint.append(')')

            else:
                raise ValueError('[%s] variable %s with incompatible relational operator' % (variable.channel_name, variable.name))

        else:
            set_constraint.append(token)


    return ' '.join(set_constraint)



def convertToSetVariables(variables, rules, constraint):
    set_variables = dict()

    variable_key_value_pairs = getVariableKeyValuePairs(variables, rules, constraint)
    for variable_key, valueset in variable_key_value_pairs.items():
        original_variable = variables[variable_key]
        set_variables[variable_key] = ExtendedSetVariable(original_variable, valueset)

    set_rules = []
    for rule in rules:
        trigger = ExtendedTrigger(rule.trigger, set_variables)
        action = ExtendedAction(rule.action, set_variables)

        rule_name = '%s%d' % ('rule', len(set_rules) + 1)
        rule = Rule(rule_name, trigger, action)
        set_rules.append(rule)

    set_constraint = convertConstraintToSetVariables(constraint, set_variables)

    return (set_variables, set_rules, set_constraint)


