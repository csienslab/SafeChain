#!/usr/bin/env python

class Custom:
    def __init__(self, channel_name, variable_name, content, variables):
        Custom.checkDefinitionErrors(channel_name, variable_name, content, variables)

        self.channel_name = channel_name
        self.variable_name = variable_name
        self.definition = content

    @classmethod
    def checkDefinitionErrors(cls, channel_name, variable_name, content, variables):
        for definition in content:
            if 'trigger' in definition:
                Custom.checkTriggerPartErrors(channel_name, variable_name, definition['trigger'], variables)

            if 'value' in content:
                variable = variables[variable_name]
                value = content['value']
                if variable.hasAssignmentErrors(value):
                    raise ValueError('[{0}] custom {1} has assignment error'.format(channel_name, variable_name))
            elif 'variable' in content:
                target_name = content['variable']
                if target_name not in variables:
                    raise ValueError('[{0}] custom {1} has unknown target'.format(channel_name, variable_name))

    @classmethod
    def hasSubjectiveErrors(cls, channel_name, variable_name, content, variables):
        if ('variable' in content and
            content['variable'] in variables):
            return False

        if ('previous' in content and
            content['previous'] in variables):
            return False

        return True

    @classmethod
    def hasObjectiveErrors(cls, channel_name, variable_name, content, variables):
        if 'value' not in content:
            return True

        return False

    @classmethod
    def checkTriggerPartErrors(cls, channel_name, variable_name, content, variables):
        if 'relationalOperator' in content:
            if Custom.hasSubjectiveErrors(channel_name, variable_name, content, variables):
                raise ValueError('[{0}] custom {1} has unknown subjective'.format(channel_name, variable_name))

            if content['relationalOperator'] not in ('<', '<=', '=', '!=', '>=', '>'):
                raise ValueError('[{0}] custom {1} has unknown relational operator'.format(channel_name, variable_name))

            if Custom.hasObjectiveErrors(channel_name, variable_name, content, variables):
                raise ValueError('[{0}] custom {1} has unknown objective target'.format(channel_name, variable_name))

            if 'variable' in content:
                variable_name = content['variable']
            elif 'previous' in content:
                variable_name = content['previous']

            variable = variables[variable_name]
            operator = content['relationalOperator']
            value = content['value']
            if variable.hasComparisonErrors(operator, value):
                raise ValueError('[{0}] custom {1} has comparison error'.format(channel_name, variable_name))

        elif 'logicalOperator' in content:
            if content['logicalOperator'] not in ('&', '|'):
                raise ValueError('[{0}] custom {1} has unknown logical operator'.format(channel_name, variable_name))

            if 'operands' not in content:
                raise ValueError('[{0}] custom {1} has unknown operands'.format(channel_name, variable_name))

            for operand in content['operands']:
                Custom.checkTriggerPartErrors(channel_name, variable_name, operand, variables)

        else:
            raise ValueError('[{0}] trigger {1} has unsupported operator'.format(channel_name, variable_name))

    def toBooleanFormat(self, content, device=''):
        if 'relationalOperator' in content:
            if 'variable' in content:
                variable = content['variable']
            elif 'previous' in content:
                variable = content['previous']

            operator = content['relationalOperator']
            value = content['value']
            return '{0} {1} {2}'.format(device + variable, operator, value)

        operator = ' {0} '.format(content['logicalOperator'])
        string = operator.join(self.toBooleanFormat(operand, device) for operand in content['operands'])
        return '({0})'.format(string)

    def getTriggersAndValues(self, variables):
        triggers_and_values = list()

        for definition in self.definition:
            if 'trigger' not in definition:
                trigger = 'TRUE'
            else:
                trigger = self.toBooleanFormat(definition['trigger'])

            if 'value' in definition:
                value = definition['value']
                if value == 'random':
                    variable = variables[self.variable_name]
                    value = variable.getPossibleValuesInNuSMV()
            elif 'variable' in definition:
                if 'operator' in definition and 'operand' in definition:
                    value = '{0} {1} {2}'.format(definition['variable'], definition['operator'], definition['operand'])
                else:
                    value = definition['variable']

            triggers_and_values.append((trigger, value))

        return triggers_and_values

    def toNuSMVformat(self, variables, device=None):
        device = '' if device == None else device + '.'

        string = 'next({0}) :=\n'.format(device + self.variable_name)
        string += '      case\n'
        for definition in self.definition:
            if 'trigger' not in definition:
                trigger = 'TRUE'
            else:
                trigger = self.toBooleanFormat(definition['trigger'], device)

            if 'value' in definition:
                value = definition['value']
                if value == 'random':
                    variable = variables[self.variable_name]
                    value = variable.getPossibleValuesInNuSMV()
            elif 'variable' in definition:
                if 'operator' in definition and 'operand' in definition:
                    value = '{0} {1} {2}'.format(definition['variable'], definition['operator'], definition['operand'])
                else:
                    value = definition['variable']

            string += '        {0}: {1};\n'.format(trigger, value)

        string += '        TRUE: {0};\n'.format(device + self.variable_name)
        string += '      esac;\n'

        return string

