#!/usr/bin/env python3

import itertools

class Trigger:
    def __init__(self, channel_name, name, content, variables):
        Trigger.checkDefinitionErrors(channel_name, name, content, variables)

        self.channel_name = channel_name
        self.name = name
        self.input_requirements = content['input']
        self.definition = content['definition']

        if self.hasInvalidInput(variables):
            raise ValueError('[{0}] trigger {1} has invalid input'.format(channel_name, name))

    @classmethod
    def checkDefinitionErrors(cls, channel_name, name, content, variables):
        if 'definition' not in content:
            raise ValueError('[{0}] trigger {1} without definition'.format(channel_name, name))

        if 'input' not in content:
            raise ValueError('[{0}] trigger {1} without input'.format(channel_name, name))

        Trigger.checkInputPartErrors(channel_name, name, content['input'], variables)
        Trigger.checkDefinitionPartErrors(channel_name, name, content['definition'], variables)

    @classmethod
    def checkInputPartErrors(cls, channel_name, name, content, variables):
        for input_requirement in content:
            if 'type' not in input_requirement:
                raise ValueError('[{0}] trigger {1} input without type'.format(channel_name, name))

            if input_requirement['type'] == 'device':
                continue

            if (input_requirement['type'] == 'value' and
                'variable' in input_requirement and
                input_requirement['variable'] in variables):
                continue

            if (input_requirement['type'] == 'set' and
                'setValue' in input_requirement and
                len(input_requirement['setValue']) != 0):
                continue

            raise ValueError('[{0}] action {1} input defined improperly'.format(channel_name, name))

    @classmethod
    def hasSubjectiveErrors(cls, channel_name, name, content, variables):
        if 'device' not in content:
            return True

        if (isinstance(content['device'], str) and
            content['device'].startswith('$') and
            content['device'][1:].isdigit()):
            return False

        if ('variable' in content and
            content['variable'] in variables):
            return False

        if ('previous' in content and
            content['previous'] in variables):
            return False

        return True

    @classmethod
    def hasObjectiveErrors(cls, channel_name, name, content, variables):
        if 'value' in content:
            if (isinstance(content['value'], str) and
                content['device'].startswith('$') and
                not content['device'][1:].isdigit()):
                return True

            return False

        if 'device2' in content:
            if ('previous2' in content and
                content['previous2'] in variables):
                return False

            return True

        return False

    @classmethod
    def checkDefinitionPartErrors(cls, channel_name, name, content, variables):
        if 'relationalOperator' in content:
            if Trigger.hasSubjectiveErrors(channel_name, name, content, variables):
                raise ValueError('[{0}] trigger {1} has unknown subjective'.format(channel_name, name))

            if (isinstance(content['relationalOperator'], str) and
                content['relationalOperator'].startswith('$') and
                not content['relationalOperator'][1:].isdigit()):
                raise ValueError('[{0}] trigger {1} has unknown relational operator index'.format(channel_name, name))

            if (isinstance(content['relationalOperator'], str) and
                not content['relationalOperator'].startswith('$') and
                content['relationalOperator'] not in ('<', '<=', '=', '!=', '>=', '>')):
                raise ValueError('[{0}] trigger {1} has unknown relational operator'.format(channel_name, name))

            if Trigger.hasObjectiveErrors(channel_name, name, content, variables):
                raise ValueError('[{0}] trigger {1} has unknown objective target'.format(channel_name, name))

        elif 'logicalOperator' in content:
            if content['logicalOperator'] not in ('&', '|'):
                raise ValueError('[{0}] trigger {1} has unknown logical operator'.format(channel_name, name))

            if 'operands' not in content:
                raise ValueError('[{0}] trigger {1} has unknown operands'.format(channel_name, name))

            for operand in content['operands']:
                Trigger.checkDefinitionPartErrors(channel_name, name, operand, variables)

        else:
            raise ValueError('[{0}] trigger {1} has unsupported operator'.format(channel_name, name))

    def genAllPossibleInputs(self, devices, variables):
        values = []
        for input_requirement in self.input_requirements:
            if input_requirement['type'] == 'device':
                value = devices
            elif input_requirement['type'] == 'value':
                variable_name = input_requirement['variable']
                variable = variables[variable_name]
                value = variable.getPossibleValues()
            elif input_requirement['type'] == 'set':
                value = input_requirement['setValue']
            else:
                raise ValueError('[{0}] action {1} with unknown input type'.format(channel_name, action_name))

            values.append(value)

        yield from itertools.product(*values)

    def hasInvalidInputRecursive(self, content, input_value, variables):
        if 'logicalOperator' in content:
            for operand in content['operands']:
                if self.hasInvalidInputRecursive(operand, input_value, variables):
                    return True

            return False

        if 'variable' in content:
            variable_name = content['variable']
        else:
            variable_name = content['previous']

        if content['relationalOperator'].startswith('$'):
            index = int(content['relationalOperator'][1:])
            operator = input_value[index]
        else:
            operator = content['relationalOperator']

        if 'previous2' in content:
            if content['previous2'] == variable_name:
                return False

            return True

        if content['value'] == 'resetValue' and variables[variable_name].reset_value != None:
            return False

        if isinstance(content['value'], str) and content['value'].startswith('$'):
            index = int(content['value'][1:])
            variable_value = input_value[index]
        else:
            variable_value = content['value']

        variable = variables[variable_name]
        return variable.hasComparisonErrors(operator, variable_value)

    def hasInvalidInput(self, variables):
        for input_value in self.genAllPossibleInputs(['trigger_device'], variables):
            if self.hasInvalidInputRecursive(self.definition, input_value, variables):
                return True

        return False
