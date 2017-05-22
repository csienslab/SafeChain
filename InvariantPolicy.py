#!/usr/bin/env python3

import Boolean as MyBoolean

class InvariantPolicy:
    def __init__(self, string):
        self.boolean = MyBoolean.Boolean(string)

    def getConstraints(self, controller):
        for condition in self.boolean.getConditions():
            yield from condition.getConstraints()

    def getRelatedVariables(self):
        for condition in self.boolean.getConditions():
            yield from condition.getVariables()

    def dumpNumvModel(self, controller):
        string = controller.dumpNumvModel()
        string += '\n'
        string += '  INVARSPEC {};\n'.format(self.boolean.getString())
        return string


