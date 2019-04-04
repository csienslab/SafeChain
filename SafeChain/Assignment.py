#!/usr/bin/env python3

import SafeChain.Condition as MyCondition

class Assignment:
    def __init__(self, string):
        self.string = string
        self.conditions = self.parser(self.string)

    def parser(self, string):
        condition_strings = string.split(',')
        conditions = list()

        for condition_string in condition_strings:
            condition = condition_string.strip().split(' ')
            condition = tuple(condition)
            condition = MyCondition.Condition(condition)

            conditions.append(condition)

        return conditions

    def getConditions(self):
        for condition in self.conditions:
            yield condition

    def getVariableAndValue(self):
        for condition in self.conditions:
            tupple = condition.getTuple()
            variable = tupple[0]
            value = ' '.join(tupple[2:])
            yield (variable, value)

    def getDependencies(self):
        for condition in self.conditions:
            channel_variables = list(condition.getVariables())
            if len(channel_variables) <= 1:
                continue

            target_channel_variable = channel_variables.pop(0)
            for channel_variable in channel_variables:
                yield (channel_variable, target_channel_variable)


