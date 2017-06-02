#!/usr/bin/env python3

# TODO getPossibleValues should comply with self.grouping

import abc
import re

class Variable(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __init__(self, device_name, definition, name):
        pass

    @abc.abstractmethod
    def getPossibleValues(self):
        pass

    @abc.abstractmethod
    def getPossibleGroups(self):
        pass

    @abc.abstractmethod
    def getPossibleGroupsInNuSMV(self):
        pass

    @abc.abstractmethod
    def setValue(self, value):
        pass

    @abc.abstractmethod
    def addConstraint(self, operator, value):
        pass

    @abc.abstractmethod
    def setGrouping(self, status):
        pass

    @abc.abstractmethod
    def setCompromised(self, status):
        pass

    @abc.abstractmethod
    def setPruned(self, status):
        pass

    @abc.abstractmethod
    def getEquivalentTriggerCondition(self, operator, value):
        pass

    @abc.abstractmethod
    def getEquivalentActionCondition(self, value):
        pass

class BooleanVariable(Variable):
    def __init__(self, device_name, definition, name):
        self.device_name = device_name
        self.definition = definition
        self.name = name
        self.value = None
        self.reset_value = definition['resetValue'] if 'resetValue' in definition else None

        self.setGrouping(False)
        self.constraints = set()

        self.compromised = False
        self.pruned = False

    def getPossibleValues(self):
        return set(['TRUE', 'FALSE'])

    def getPossibleGroups(self):
        return set(self.mapping.values())

    def getPossibleGroupsInNuSMV(self):
        if len(self.getPossibleGroups()) == 1:
            return '{ALL}'
        else:
            return 'boolean'

    def setValue(self, value):
        self.value = value

    def addConstraint(self, operator, value):
        if isinstance(value, str) and '{' in value:
            value = value.replace('{', '').replace('}', '').replace(' ', '')
            values = value.split(',')
            for value in values:
                self.constraints.add((operator, value))
        else:
            self.constraints.add((operator, value))

    def setGrouping(self, status):
        self.grouped = False
        if status != True:
            self.mapping = dict((value, value) for value in self.getPossibleValues())
            return

        values = set(value for operator, value in self.constraints)
        if None in values:
            self.mapping = dict((value, value) for value in self.getPossibleValues())
            return

        self.grouped = True
        if len(values) == 0:
            self.mapping = dict((value, 'ALL') for value in self.getPossibleValues())
        else:
            self.mapping = dict((value, value) if value in values else (value, 'OTHERS') for value in self.getPossibleValues())

    def getEquivalentTriggerCondition(self, operator, value):
        return (operator, value)

    def getEquivalentActionCondition(self, value):
        if not self.grouped:
            return value

        if isinstance(value, str) and '{' in value:
            value = value.replace('{', '').replace('}', '').replace(' ', '')
            values = value.split(',')
            values = set(self.mapping[value] for value in values)
        else:
            values = set([self.mapping[value]])

        if len(values) > 1:
            values = sorted(values)
            return '{{{0}}}'.format(', '.join(values))
        else:
            value = values.pop()
            return value

    def setCompromised(self, status):
        self.compromised = status

    def setPruned(self, status):
        self.pruned = status

class SetVariable(Variable):
    def __init__(self, device_name, definition, name):
        self.device_name = device_name
        self.definition = definition
        self.name = name
        self.value = None
        self.reset_value = definition['resetValue'] if 'resetValue' in definition else None

        self.setGrouping(False)
        self.constraints = set()

        self.compromised = False
        self.pruned = False

    def getPossibleValues(self):
        return set(self.definition['setValue'])

    def getPossibleGroups(self):
        return set(self.mapping.values())

    def getPossibleGroupsInNuSMV(self):
        groups = sorted(self.getPossibleGroups())
        string = ', '.join(groups)
        return '{{{0}}}'.format(string)

    def setValue(self, value):
        self.value = value

    def addConstraint(self, operator, value):
        if isinstance(value, str) and '{' in value:
            value = value.replace('{', '').replace('}', '').replace(' ', '')
            values = value.split(',')
            for value in values:
                self.constraints.add((operator, value))
        else:
            self.constraints.add((operator, value))

    def setGrouping(self, status):
        self.grouped = False
        if status != True:
            self.mapping = dict((value, value) for value in self.getPossibleValues())
            return

        values = set(value for operator, value in self.constraints)
        if None in values:
            self.mapping = dict((value, value) for value in self.getPossibleValues())
            return

        self.grouped = True
        if len(values) == 0:
            self.mapping = dict((value, 'ALL') for value in self.getPossibleValues())
        elif len(values) >= len(self.getPossibleValues()) - 1:
            self.mapping = dict((value, value) for value in self.getPossibleValues())
        else:
            self.mapping = dict((value, value) if value in values else (value, 'OTHERS') for value in self.getPossibleValues())

    def getEquivalentTriggerCondition(self, operator, value):
        return (operator, value)

    def getEquivalentActionCondition(self, value):
        if not self.grouped:
            return value

        if isinstance(value, str) and '{' in value:
            value = value.replace('{', '').replace('}', '').replace(' ', '')
            values = value.split(',')
            values = set(self.mapping[value] for value in values)
        else:
            values = set([self.mapping[value]])

        if len(values) > 1:
            values = sorted(values)
            return '{{{0}}}'.format(', '.join(values))
        else:
            value = values.pop()
            return value

    def setCompromised(self, status):
        self.compromised = status

    def setPruned(self, status):
        self.pruned = status

class RangeVariable(Variable):
    def __init__(self, device_name, definition, name):
        self.device_name = device_name
        self.definition = definition
        self.name = name
        self.value = None
        self.reset_value = definition['resetValue'] if 'resetValue' in definition else None

        self.setGrouping(False)
        self.constraints = set()

        self.compromised = False
        self.pruned = False

    def getPossibleValues(self):
        return set(range(self.definition['minValue'], self.definition['maxValue'] + 1))

    def getPossibleGroups(self):
        if 'window' in self.definition:
            minValue = max(self.definition['minValue'], self.value - self.definition['window'])
            maxValue = min(self.definition['maxValue'], self.value + self.definition['window'])
            return set(self.mapping[i] for i in range(minValue, maxValue+1))

        return set(self.mapping.values())

    def getPossibleGroupsInNuSMV(self):
        if self.grouped:
            groups = sorted(self.getPossibleGroups())
            string = ', '.join(groups)
            return '{{{0}}}'.format(string)
        elif 'window' in self.definition:
            minValue = max(self.definition['minValue'], self.value - self.definition['window'])
            maxValue = min(self.definition['maxValue'], self.value + self.definition['window'])
            return '{0}..{1}'.format(minValue, maxValue)
        else:
            return '{0}..{1}'.format(self.definition['minValue'], self.definition['maxValue'])

    def setValue(self, value):
        self.value = value

        if 'window' in self.definition:
            minValue = max(self.definition['minValue'], self.value - self.definition['window'])
            maxValue = min(self.definition['maxValue'], self.value + self.definition['window'])
            self.addConstraint('>=', minValue)
            self.addConstraint('<=', maxValue)

    def addConstraint(self, operator, value):
        if isinstance(value, str) and '{' in value:
            value = value.replace('{', '').replace('}', '').replace(' ', '')
            values = value.split(',')
            for value in values:
                self.addConstraint(operator, value)
        elif isinstance(value, str) and '..' in value:
            minValue, maxValue = value.split('..')
            self.addConstraint('>=', minValue)
            self.addConstraint('<=', maxValue)
        elif operator == '>=':
            value = int(value)
            if value > self.definition['minValue']:
                self.constraints.add(('>', value - 1))
        elif operator == '<=':
            value = int(value)
            if value < self.definition['maxValue']:
                self.constraints.add(('<', value + 1))
        else:
            self.constraints.add((operator, value))

    def setGrouping(self, status):
        self.grouped = False
        if status != True:
            self.mapping = dict((value, value) for value in self.getPossibleValues())
            return

        values = set(value for operator, value in self.constraints)
        if None in values:
            self.mapping = dict((value, value) for value in self.getPossibleValues())
            return

        self.grouped = True

        if len(values) == 0:
            self.mapping = dict((value, 'ALL') for value in self.getPossibleValues())
            return

        continuous = False
        for operator, value in self.constraints:
            if '>' in operator or '<' in operator:
                continuous = True

        values = set(int(value) for value in values)
        if not continuous:
            if len(values) >= len(self.getPossibleValues()) - 1:
                self.mapping = dict((value, str(value)) for value in self.getPossibleValues())
            else:
                self.mapping = dict((value, str(value)) if value in values else (value, 'OTHERS') for value in self.getPossibleValues())
        else:
            self.mapping = dict()
            values = sorted(values)
            if self.definition['minValue'] not in values:
                for value in range(self.definition['minValue'], values[0]):
                    self.mapping[value] = 'between_min_{}'.format(values[0])

            for i in range(len(values) - 1):
                self.mapping[values[i]] = '{}'.format(values[i])
                for value in range(values[i] + 1, values[i+1]):
                    self.mapping[value] = 'between_{0}_{1}'.format(values[i], values[i+1])
            self.mapping[values[-1]] = '{}'.format(values[-1])

            if self.definition['maxValue'] not in values:
                for value in range(values[-1] + 1, self.definition['maxValue'] + 1):
                    self.mapping[value] = 'between_{}_max'.format(values[-1])


    def getEquivalentTriggerCondition(self, operator, value):
        if not self.grouped:
            return (operator, value)

        if 'window' in self.definition:
            minValue = max(self.definition['minValue'], self.value - self.definition['window'])
            maxValue = min(self.definition['maxValue'], self.value + self.definition['window'])
        else:
            minValue = self.definition['minValue']
            maxValue = self.definition['maxValue']

        if operator in ('=', '!='):
            if 'window' in self.definition:
                if int(value) >= minValue and int(value) <= maxValue:
                    return (operator, value)
                else:
                    return ('in', '{}')
            else:
                return (operator, value)

        if operator == '>':
            minValue = max(int(value) + 1, minValue)
        elif operator == '>=':
            minValue = max(int(value), minValue)
        elif operator == '<':
            maxValue = min(int(value) - 1, maxValue)
        elif operator == '<=':
            maxValue = min(int(value), maxValue)
        else:
            return (operator, value)

        values = set(self.mapping[value] for value in range(minValue, maxValue+1))
        if len(values) == 1:
            value = values.pop()
            return ('=', value)
        else:
            return ('in', '{{{0}}}'.format(', '.join(str(value) for value in values)))


    def getEquivalentActionCondition(self, value):
        if not self.grouped:
            return value

        if isinstance(value, str) and '{' in value:
            value = value.replace('{', '').replace('}', '').replace(' ', '')
            values = value.split(',')
            values = set(self.mapping[value] for value in values)
        elif isinstance(value, str) and '..' in value:
            minValue, maxValue = value.split('..')
            values = set(self.mapping[value] for value in range(int(minValue), int(maxValue)+1))
        else:
            values = set([self.mapping[int(value)]])

        if len(values) == 1:
            value = values.pop()
            return value
        else:
            values = sorted(values)
            return '{{{0}}}'.format(', '.join(values))

    def setCompromised(self, status):
        self.compromised = status

    def setPruned(self, status):
        self.pruned = status
