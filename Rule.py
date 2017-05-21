#!/usr/bin/env python3

class Rule:
    def __init__(self, name, trigger, action):
        self.name = name
        self.trigger = trigger
        self.action = action

    def getConditions(self):
        yield from self.trigger.getConditions()
        yield from self.action.getConditions()

    def getTransitions(self):
        trigger_boolean = self.trigger.getBooleanString()

        for action_boolean, variable, value in self.action.getTransitions():
            if trigger_boolean != 'TRUE' and action_boolean != 'TRUE':
                boolean = '({0}) & ({1})'.format(trigger_boolean, action_boolean)
            elif trigger_boolean != 'TRUE':
                boolean = trigger_boolean
            elif action_boolean != 'TRUE':
                boolean = action_boolean
            else:
                boolean = 'TRUE'

            yield (boolean, variable, value)
