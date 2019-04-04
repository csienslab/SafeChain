#!/usr/bin/env python3

import copy
import re

class Condition:
    def __init__(self, tupple):
        self.original = copy.copy(tupple)
        self.tupple = copy.copy(tupple)
        self.variable_pattern = re.compile('\w+\.\w+')

    def getConstraints(self):
        if len(self.tupple) != 3:
            # computation or true
            for channel_name, variable_name in self.getVariables():
                yield (channel_name, variable_name, None, None)
            return

        subject, operator, value = self.tupple
        channel_name, variable_name = subject.split('.')

        if self.variable_pattern.fullmatch(value):
            # assign variable to variable or comparison between variables
            yield (channel_name, variable_name, '≡', value)
        else:
            yield (channel_name, variable_name, operator, value)

    def getVariables(self):
        for token in self.tupple:
            if self.variable_pattern.fullmatch(token) == None:
                continue

            channel_name, variable_name = token.split('.')
            yield (channel_name, variable_name)

    def toEquivalentCondition(self, controller):
        if len(self.tupple) != 3:
            return

        subject, operator, value = self.tupple
        if self.variable_pattern.fullmatch(value):
            # assign variable to variable or comparison between variables
            return

        channel_name, variable_name = subject.split('.')
        channel = controller.getDevice(channel_name)
        variable = channel.getVariable(variable_name)
        if operator != '←':
            operator, value = variable.getEquivalentTriggerCondition(operator, value)
        else:
            value = variable.getEquivalentActionCondition(value)

        if value != '{}':
            self.tupple = (subject, operator, value)
        else:
            self.tupple = ('FALSE', )

    def toOriginal(self):
        self.tupple = copy.copy(self.original)

    def getString(self):
        return ' '.join(self.tupple)

    def getTuple(self):
        return self.tupple

