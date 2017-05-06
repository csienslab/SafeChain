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


class BooleanVariable(Variable):
    def __init__(self, channel_name, name, content):
        super().__init__(channel_name, name, content)

        self.channel_name = channel_name
        self.name = name
        if 'previous' in content and content['previous'] == 'true':
            self.previous = True
        else:
            self.previous = False

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

class SetVariable(Variable):
    def __init__(self, channel_name, name, content):
        super().__init__(channel_name, name, content)

        self.channel_name = channel_name
        self.name = name
        self.value_set = content['setValue']
        if 'previous' in content and content['previous'] == 'true':
            self.previous = True
        else:
            self.previous = False

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

class RangeVariable(Variable):
    def __init__(self, channel_name, name, content):
        super().__init__(channel_name, name, content)

        self.channel_name = channel_name
        self.name = name
        self.min_value = content['minValue']
        self.max_value = content['maxValue']
        self.reset_value = content['resetValue'] if 'resetValue' in content else None
        if 'previous' in content and content['previous'] == 'true':
            self.previous = True
        else:
            self.previous = False

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

class TimerVariable(Variable):
    def __init__(self, channel_name, name, content):
        super().__init__(channel_name, name, content)

        self.channel_name = channel_name
        self.name = name
        self.max_value = content['maxValue']
        self.repeat = (content['repeat'] == 'true')
        if 'previous' in content and content['previous'] == 'true':
            self.previous = True
        else:
            self.previous = False

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




