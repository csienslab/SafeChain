#!/usr/bin/env python3

import copy

class Condition:
    def __init__(self, tupple):
        self.original = copy.copy(tupple)
        self.tupple = copy.copy(tupple)

    def getConstraints(self, controller):
        if len(self.tupple) != 3:
            # computation or true
            for device_name, variable_name in self.getVariables(controller):
                yield (device_name, variable_name, None, None)
            raise StopIteration

        subject, operator, value = self.tupple
        if value.startswith(subject) or subject.startswith(value):
            # previous
            raise StopIteration

        if subject.endswith('_previous'):
            subject = subject[:-9]

        device_name, variable_name = subject.split('.')
        yield (device_name, variable_name, operator, value)

    def getVariables(self, controller):
        for token in self.tupple:
            if '.' not in token:
                continue

            if token.endswith('_previous'):
                token = token[:-9]

            device_name, variable_name = token.split('.')
            if controller.hasVariable(device_name, variable_name):
                yield (device_name, variable_name)

    def toEquivalentCondition(self, controller):
        if len(self.tupple) != 3:
            return

        subject, operator, value = self.tupple
        if value.startswith(subject) or subject.startswith(value):
            # previous
            return

        device_name, variable_name = subject.split('.')
        if variable_name.endswith('_previous'):
            variable_name = variable_name[:-9]

        device = controller.getDevice(device_name)
        variable = device.getVariable(variable_name)
        if operator != '←':
            operator, value = variable.getEquivalentTriggerCondition(operator, value)
        else:
            value = variable.getEquivalentActionCondition(value)

        if value != '{}':
            self.tupple = (subject, operator, value)
        else:
            self.tupple = ('FALSE', )

    def getString(self):
        return ' '.join(self.tupple)

    def getTuple(self):
        return self.tupple

