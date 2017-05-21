#!/usr/bin/env python3

import Boolean as MyBoolean

class Trigger:
    def __init__(self, rule_name, channel_name, definition, name, parameters):
        self.rule_name = rule_name
        self.channel_name = channel_name
        self.definition = definition
        self.name = name
        self.parameters = parameters

        boolean_definition = self.definition['definition']['boolean']
        boolean_string = boolean_definition.format(*parameters)
        self.boolean = MyBoolean.Boolean(boolean_string)

    def getConditions(self):
        yield from self.boolean.getConditions()

    def getBooleanString(self):
        return self.boolean.getString()

