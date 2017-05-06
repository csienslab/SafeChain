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
                content['value'].startswith('$') and
                not content['value'][1:].isdigit()):
                return True

            return False

        if ('previous2' in content and
            content['previous2'] in variables):
            if (isinstance(content['device2'], str) and
                content['device2'].startswith('$') and
                content['device2'][1:].isdigit()):
                return False

            return True

        return True

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

    def getRequiredDevices(self, inputs):
        devices = set()
        for input_requirement, value in zip(self.input_requirements, inputs):
            if input_requirement['type'] != 'device':
                continue

            devices.add(value)

        return devices

    def getRequiredVariables(self, content=None):
        if content == None:
            content = self.definition

        if 'logicalOperator' in content:
            variables = set()
            for operand in content['operands']:
                variables |= self.getRequiredVariables(operand)

            return variables

        variables = set()
        if 'variable' in content:
            variables.add(content['variable'])
        else:
            variables.add(content['previous'])

        if 'previous2' in content:
            variables.add(content['previous2'])

        return variables

    def toBooleanString(self, inputs, content=None):
        if content == None:
            content = self.definition

        if 'logicalOperator' in content:
            booleans = list()
            for operand in content['operands']:
                booleans.append('({})'.format(self.toBooleanString(inputs, operand)))

            operator = ' {} '.format(content['logicalOperator'])
            return operator.join(booleans)

        index = int(content['device'][1:])
        device = inputs[index]
        if 'variable' in content:
            sub = '{0}.{1}'.format(device, content['variable'])
        elif 'previous' in content:
            sub = '{0}.{1}'.format(device, content['previous'] + '_previous')

        if 'value' in content:
            if (isinstance(content['value'], str) and
                content['value'].startswith('$')):
                index = int(content['value'][1:])
                obj = inputs(index)
            else:
                obj = content['value']

        elif 'previous2' in content:
            if (isinstance(content['device2'], str) and
                content['device2'].startswith('$')):
                index2 = int(content['device2'][1:])
                device2 = inputs[index2]
            obj = '{0}.{1}'.format(device2, content['previous2'] + '_previous')

        return '{0} {1} {2}'.format(sub, content['relationalOperator'], obj)


