#!/usr/bin/env python3

import itertools

class Rule:
    def __init__(self, name, trigger, action):
        self.name = name
        self.trigger = trigger
        self.action = action

    def getTriggerConditions(self):
        yield from self.trigger.getConditions()
        yield from self.action.getTriggerConditions()

    def getActionConditions(self):
        yield from self.action.getActionConditions()

    def getConditions(self):
        yield from self.getTriggerConditions()
        yield from self.getActionConditions()

    def getVariables(self):
        for condition in self.getConditions():
            yield from condition.getVariables()

    def getTransitions(self):
        trigger_boolean = self.trigger.getBooleanString()

        for action_boolean, variable, value in self.action.getTransitions():
            if trigger_boolean != 'TRUE' and action_boolean != 'TRUE':
                boolean = '( {0} ) & ( {1} )'.format(trigger_boolean, action_boolean)
            elif trigger_boolean != 'TRUE':
                boolean = trigger_boolean
            elif action_boolean != 'TRUE':
                boolean = action_boolean
            else:
                boolean = 'TRUE'

            yield (boolean, variable, value)

    def getDependencies(self):
        trigger_variables = set(variable for condition in self.getTriggerConditions() for variable in condition.getVariables())
        action_variables = set(variable for condition in self.getActionConditions() for variable in condition.getVariables())

        yield from itertools.product(trigger_variables, action_variables)
