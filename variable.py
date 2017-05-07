#!/usr/bin/env python3

# TODO: check -> has

import abc

class Variable(metaclass=abc.ABCMeta):
    def __init__(self, channel_name, name, content):
        Variable.checkDefinitionErrors(channel_name, name, content)

    @classmethod
    @abc.abstractmethod
    def checkDefinitionErrors(cls, channel_name, name, content):
        pass

    @abc.abstractmethod
    def hasComparisonErrors(self, operator, value):
        pass

    @abc.abstractmethod
    def hasAssignmentErrors(self, value):
        pass

    @abc.abstractmethod
    def getPossibleValues(self):
        pass

    @abc.abstractmethod
    def getPossibleValuesInNuSMV(self):
        pass

    @abc.abstractmethod
    def getPossibleValuesInNuSMVwithConstraints(self, constraints):
        pass

    @abc.abstractmethod
    def getEquivalentAssignmentWithConstraints(self, constraints, assignment_value):
        pass

    @abc.abstractmethod
    def getEquivalentComparisonWithConstraints(self, constraints, comparison_operator, comparison_value):
        pass

class BooleanVariable(Variable):
    def __init__(self, channel_name, name, content):
        super().__init__(channel_name, name, content)

        self.channel_name = channel_name
        self.name = name
        self.previous = ('previous' in content and content['previous'] == 'true')
        self.split_points = set()

    @classmethod
    def checkDefinitionErrors(cls, channel_name, name, content):
        if content['type'] != 'boolean':
            raise ValueError('[{0}] variable {1} with unsupported type {2}'.format(channel_name, name, content['type']))

        return None

    def hasComparisonErrors(self, operator, value):
        if operator not in ('=', '!='):
            return True

        if value not in ('TRUE', 'FALSE'):
            return True

        return False

    def hasAssignmentErrors(self, value):
        if value in ('TRUE', 'FALSE', 'random', 'toggle'):
            return False

        return True

    def getPossibleValues(self):
        return ['TRUE', 'FALSE']

    def getPossibleValuesInNuSMV(self):
        return '{TRUE, FALSE}'

    def getPossibleValuesInNuSMVwithConstraints(self, constraints):
        if len(constraints) == 0:
            return '{ALL}'
        else:
            return '{TRUE, FALSE}'

    def getEquivalentAssignmentWithConstraints(self, constraints, assignment_value):
        if len(constraints) == 0:
            return 'ALL'
        else:
            return value

    def getEquivalentComparisonWithConstraints(self, constraints, comparison_operator, comparison_value):
        if len(constraints) == 0:
            raise ValueError('[GG1]')
        return (comparison_operator, comparison_value)

class SetVariable(Variable):
    def __init__(self, channel_name, name, content):
        super().__init__(channel_name, name, content)

        self.channel_name = channel_name
        self.name = name
        self.value_set = content['setValue']
        self.previous = ('previous' in content and content['previous'] == 'true')

    @classmethod
    def checkDefinitionErrors(cls, channel_name, name, content):
        if content['type'] != 'set':
            raise ValueError('[{0}] variable {1} with unsupported type {2}'.format(channel_name, name, content['type']))

        if 'setValue' not in content:
            raise ValueError('[{0}] variable {1} with undefined setValue'.format(channel_name, name))

        if len(content['setValue']) == 0:
            raise ValueError('[{0}] variable {1} with empty setValue'.format(channel_name, name))

        return None

    def hasComparisonErrors(self, operator, value):
        if operator not in ('=', '!='):
            return True

        if value not in self.value_set:
            return True

        return False

    def hasAssignmentErrors(self, value):
        if value in self.value_set:
            return False

        if value == 'random':
            return False

        if value == 'toggle' and len(self.value_set) == 2:
            return False

        return True

    def getPossibleValues(self):
        return list(self.value_set)

    def getPossibleValuesInNuSMV(self):
        return '{{{0}}}'.format(', '.join(str(x) for x in self.value_set))

    def getPossibleValuesInNuSMVwithConstraints(self, constraints):
        values = set()
        for operator, value in constraints:
            if value == None:
                return self.getPossibleValuesInNuSMV()

            values.add(value)

        if len(values) == 0:
            return '{ALL}'
        elif (len(values) == len(self.getPossibleValues()) - 1 or
              len(values) == len(self.getPossibleValues())):
            return self.getPossibleValuesInNuSMV()
        else:
            values.add('OTHERS')
            return '{{{0}}}'.format(', '.join(str(x) for x in values))

    def getEquivalentAssignmentWithConstraints(self, constraints, assignment_value):
        values = set()
        for operator, value in constraints:
            if value == None:
                return assignment_value

            values.add(value)

        if len(values) == 0:
            return 'ALL'
        elif (len(values) == len(self.getPossibleValues()) - 1 or
              len(values) == len(self.getPossibleValues())):
            return assignment_value
        elif value in values:
            return assignment_value
        else:
            return 'OTHERS'

    def getEquivalentComparisonWithConstraints(self, constraints, comparison_operator, comparison_value):
        if len(constraints) == 0:
            raise ValueError('[GG1]')
        return (comparison_operator, comparison_value)

class RangeVariable(Variable):
    def __init__(self, channel_name, name, content):
        super().__init__(channel_name, name, content)

        self.channel_name = channel_name
        self.name = name
        self.min_value = content['minValue']
        self.max_value = content['maxValue']
        self.reset_value = content['resetValue'] if 'resetValue' in content else None
        self.previous = ('previous' in content and content['previous'] == 'true')

    @classmethod
    def checkDefinitionErrors(cls, channel_name, name, content):
        if content['type'] != 'range':
            raise ValueError('[{0}] variable {1} with unsuppported type {2}'.format(channel_name, name, content['type']))

        if 'minValue' not in content:
            raise ValueError('[{0}] variable {1} with undefined minValue'.format(channel_name, name))

        if 'maxValue' not in content:
            raise ValueError('[{0}] variable {1} with undefined maxValue'.format(channel_name, name))

        if not isinstance(content['minValue'], int) or not isinstance(content['maxValue'], int):
            raise ValueError('[{0}] variable {1} with unsupported minValue or maxValue'.format(channel_name, name))

        if 'resetValue' in content:
            if not isinstance(content['resetValue'], int):
                raise ValueError('[{0}] variable {1} with unsupported resetValue'.format(channel_name, name))

            if content['resetValue'] < content['minValue'] or content['resetValue'] > content['maxValue']:
                raise ValueError('[{0}] variable {1} with outside resetValue'.format(channel_name, name))

        return None

    def hasComparisonErrors(self, operator, value):
        if operator not in ('<', '<=', '=', '!=', '>=', '>'):
            return True

        if not isinstance(value, int):
            return True

        if value < self.min_value or value > self.max_value:
            return True

        return False

    def hasAssignmentErrors(self, value):
        if value == 'random':
            return False

        if (isinstance(value, int) and
            value >= self.min_value and
            value <= self.max_value):
            return False

        return True

    def getPossibleValues(self):
        return list(range(self.min_value, self.max_value + 1))

    def getPossibleValuesInNuSMV(self):
        return '{0}..{1}'.format(self.min_value, self.max_value)

    def getPossibleValuesInNuSMVwithConstraints(self, constraints):
        continuous = False
        values = set()

        for operator, value in constraints:
            if operator not in ('=', '!='):
                continuous = True

            if value == None:
                return self.getPossibleValuesInNuSMV()

            values.add(value)

        if len(values) == 0:
            return '{ALL}'

        if continuous:
            results = list()
            values = sorted(values)
            if self.min_value not in values:
                results.append('between_min_{}'.format(values[0]))

            for i in range(len(values) - 1):
                results.append('{}'.format(values[i]))
                results.append('between_{0}_{1}'.format(values[i], values[i+1]))
            results.append('{}'.format(values[-1]))

            if self.max_value not in values:
                results.append('between_{}_max'.format(values[-1]))

            return '{{{0}}}'.format(', '.join(results))
        else:
            if (len(values) == len(self.getPossibleValues()) or
                len(values) == len(self.getPossibleValues()) - 1):
                return self.getPossibleValuesInNuSMV()

            results = sorted(values)
            results.append('OTHERS')
            return '{' + ', '.join('{}'.format(x) for x in results) + '}'

    def getEquivalentAssignmentWithConstraints(self, constraints, assignment_value):
        continuous = False
        values = set()

        for operator, value in constraints:
            if operator not in ('=', '!='):
                continuous = True

            if value == None:
                return assignment_value

            values.add(value)

        if len(values) == 0:
            return 'ALL'

        if continuous:
            if assignment_value in values:
                return '{}'.format(assignment_value)

            values.add(assignment_value)
            values = sorted(values)
            index = values.index(assignment_value)
            if index == 0:
                return 'between_min_{}'.format(values[index+1])
            elif index == len(values) - 1:
                return 'between_{}_max'.format(values[index-1])
            else:
                return 'between_{}_{}'.format(values[index-1], values[index+1])
        else:
            if (len(values) == len(self.getPossibleValues()) or
                len(values) == len(self.getPossibleValues()) - 1):
                return assignment_value

            if assignment_value in values:
                return assignment_value

            return 'OTHERS'

    def getEquivalentComparisonWithConstraints(self, constraints, comparison_operator, comparison_value):
        if comparison_operator in ('=', '!='):
            return (comparison_operator, comparison_value)

        continuous = False
        values = set()

        for operator, value in constraints:
            if operator not in ('=', '!='):
                continuous = True

            if value == None:
                return (comparison_operator, comparison_value)

            values.add(value)

        if len(values) == 0:
            raise ValueError('[GG3]')

        results = list()
        values = sorted(values)
        index = values.index(comparison_value)
        if '<' in comparison_operator:
            if self.min_value not in values:
                results.append('between_min_{}'.format(values[0]))
            for i in range(index):
                results.append('{}'.format(values[i]))
                results.append('between_{0}_{1}'.format(values[i], values[i+1]))

        if '>' in comparison_operator:
            if self.max_value not in values:
                results.append('between_{}_max'.format(values[-1]))

            for i in range(len(values) - 1, index, -1):
                results.append('{}'.format(values[i]))
                results.append('between_{0}_{1}'.format(values[i-1], values[i]))

        if '=' in comparison_operator:
            results.append('{}'.format(values[index]))

        if '>' in comparison_operator:
            results = reversed(results)

        return ('in', '{{{0}}}'.format(', '.join(results)))

class TimerVariable(Variable):
    def __init__(self, channel_name, name, content):
        super().__init__(channel_name, name, content)

        self.channel_name = channel_name
        self.name = name
        self.max_value = content['maxValue']
        self.repeat = (content['repeat'] == 'true')
        self.previous = ('previous' in content and content['previous'] == 'true')

    @classmethod
    def checkDefinitionErrors(cls, channel_name, name, content):
        if content['type'] != 'timer':
            raise ValueError('[{0}] variable {1} with unsuppported type {2}'.format(channel_name, name, content['type']))

        if 'maxValue' not in content:
            raise ValueError('[{0}] variable {1} with undefined maxValue'.format(channel_name, name))

        if not isinstance(content['maxValue'], int):
            raise ValueError('[{0}] variable {1} with unsupported maxValue'.format(channel_name, name))

        if 'repeat' not in content:
            raise ValueError('[{0}] variable {1} with undefined repeat'.format(channel_name, name))

        if content['repeat'] not in ('true', 'false'):
            raise ValueError('[{0}] variable {1} with unsupported repeat'.format(channel_name, name))

        return None

    def hasComparisonErrors(self, operator, value):
        if operator not in ('=', '!='):
            return True

        if (isinstance(value, int) and
            value <= self.max_value and
            value >= -1):
            return False

        return True

    def hasAssignmentErrors(self, value):
        if (isinstance(value, int) and
            value <= self.max_value and
            value >= -1):
            return False

        return True

    def getPossibleValues(self):
        return list(range(0, self.max_value + 1))

    def getPossibleValuesInNuSMV(self):
        if self.repeat:
            min_value = 0
        else:
            min_value = -1

        return '{}..{}'.format(min_value, self.max_value)

    def getPossibleValuesInNuSMVwithConstraints(self, constraints):
        return self.getPossibleValuesInNuSMV()

    def getEquivalentAssignmentWithConstraints(self, constraints, assignment_value):
        return assignment_value

    def getEquivalentComparisonWithConstraints(self, constraints, operator, comparison_value):
        return (operator, comparison_value)
