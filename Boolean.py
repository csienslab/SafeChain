#!/usr/bin/env python3

import Condition as MyCondition

class Boolean:
    def __init__(self, string):
        self.string = string
        self.infix_tokens = self.parser(self.string)

    def tokenize(self, string):
        return string.split(' ')

    def parser(self, string):
        tokens = self.tokenize(string)
        infix_tokens = []

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in ('(', ')', '&', '|', '!'):
                infix_tokens.append(token)
                i += 1
                continue

            bool_condition = [token]
            i += 1

            while i < len(tokens) and tokens[i] not in ('(', ')', '&', '|', '!'):
                bool_condition.append(tokens[i])
                bool_condition.append(tokens[i+1])
                i += 2

            bool_condition = tuple(bool_condition)
            bool_condition = MyCondition.Condition(bool_condition)
            infix_tokens.append(bool_condition)

        return tuple(infix_tokens)

    def getConditions(self):
        for token in self.infix_tokens:
            if token in ('(', ')', '&', '|', '!'):
                continue

            yield token

    def getString(self):
        tokens = []
        for token in self.infix_tokens:
            if token in ('(', ')', '&', '|', '!'):
                tokens.append(token)
                continue

            string = token.getString()
            tokens.append(string)

        return ' '.join(tokens)


