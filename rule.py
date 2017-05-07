#!/usr/bin/env python

class Rule:
    def __init__(self, name, trigger, trigger_inputs, action, action_inputs):
        self.name = name
        self.trigger = trigger
        self.trigger_inputs = trigger_inputs
        self.action = action
        self.action_inputs = action_inputs

    def getAssociatedDeviceVariableOperatorAndValue(self, variables):
        results = self.trigger.getAssociatedDeviceVariableOperatorAndValue(self.trigger_inputs)
        return results
