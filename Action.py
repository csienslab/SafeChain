#!/usr/bin/env python3

import Boolean as MyBoolean
import Assignment as MyAssignment

class Action:
    def __init__(self, rule_name, channel_name, definition, name, parameters):
        self.rule_name = rule_name
        self.channel_name = channel_name
        self.definition = definition
        self.name = name
        self.parameters = parameters

        self.situations = list()
        for situation in self.definition['definition']:
            if 'boolean' in situation:
                boolean_definition = situation['boolean']
                boolean_string = boolean_definition.format(*parameters)
                boolean = MyBoolean.Boolean(boolean_string)
            else:
                boolean = None

            assignment_definition = situation['assignment']
            assignment_string = assignment_definition.format(*parameters)
            assignment = MyAssignment.Assignment(assignment_string)

            self.situations.append((boolean, assignment))

    def getTriggerConditions(self):
        for boolean, assignment in self.situations:
            if boolean != None:
                yield from boolean.getConditions()

    def getActionConditions(self):
        for boolean, assignment in self.situations:
            yield from assignment.getConditions()

    def getTransitions(self):
        for boolean, assignment in self.situations:
            if boolean != None:
                boolean_string = boolean.getString()
            else:
                boolean_string = 'TRUE'

            for variable_name, value in assignment.getVariableAndValue():
                yield (boolean_string, variable_name, value)

    def getDependencies(self):
        for boolean, assignment in self.situations:
            yield from assignment.getDependencies()



