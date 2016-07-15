#!/usr/bin/python3

import copy

'''
Grammar
expression := boolean
              | (expression)
              | !expression
              | boolean & expression
              | boolean | expression

boolean := subject relationop value
relationop := = | != | < | <= | > | >=
'''

def flattenList(l):
    if not isinstance(l, list):
        yield l
        return

    for element in l:
        yield from flattenList(element)

def tokenParser(plain_string):
    space_splitted = plain_string.split(' ')
    infix_tokens = []

    i = 0
    while i < len(space_splitted):
        token = space_splitted[i]
        if token not in ['(', ')', '!', '&', '|']:
            bool_expr = (token, space_splitted[i+1], space_splitted[i+2])
            infix_tokens.append(bool_expr)
            i += 3
        else:
            infix_tokens.append(token)
            i += 1

    return infix_tokens

def checkPrecedence(prev_op, cur_op):
    if cur_op == '(':
        return False
    elif cur_op == '&' or cur_op == '|':
        return prev_op in ['!', '|', '&']
    elif cur_op == '!':
        return False
    else:
        raise ValueError('wrong boolean operator %s' % cur_op)

def infixToPostfix(infix_tokens):
    actions = []
    postfix_tokens = []

    for token in infix_tokens:
        if token not in ['(', ')', '!', '&', '|']:
            postfix_tokens.append(token)
        elif token == ')':
            while actions[-1] != '(':
                bool_op = actions.pop()
                postfix_tokens.append(bool_op)
            actions.pop()
        else:
            while len(actions) != 0 and checkPrecedence(actions[-1], token):
                bool_op = actions.pop()
                postfix_tokens.append(bool_op)
            actions.append(token)

    while len(actions) != 0:
        bool_op = actions.pop()
        postfix_tokens.append(bool_op)

    return postfix_tokens

def getInverseCondition(postfix):
    if isinstance(postfix, tuple):
        obj, old_op, val = postfix
        if old_op == '=':
            new_op = '!='
        elif old_op == '!=':
            new_op = '='
        elif old_op == '<':
            new_op = '>='
        elif old_op == '<=':
            new_op = '>'
        elif old_op == '>':
            new_op = '<='
        elif old_op == '>=':
            new_op = '<'
        else:
            raise ValueError('wrong relational operator %s' % old_op)

        return (obj, new_op, val)

    old_token = postfix[2]
    if old_token == '&':
        new_token = '|'
    elif old_token == '|':
        new_token = '&'
    else:
        raise ValueError('wrong boolean operator %s' % token)

    left_bool_expr = getInverseCondition(postfix[0])
    right_bool_expr = getInverseCondition(postfix[1])
    return [left_bool_expr, right_bool_expr, new_token]

def expandNotOperator(postfix_tokens):
    new_postfix_tokens = []

    for token in postfix_tokens:
        if isinstance(token, tuple):
            new_postfix_tokens.append(token)
        elif token == '&' or token == '|':
            right_bool_expr = new_postfix_tokens.pop()
            left_bool_expr = new_postfix_tokens.pop()
            new_postfix_tokens.append([left_bool_expr, right_bool_expr, token])
        elif token == '!':
            bool_expr = new_postfix_tokens.pop()
            new_bool_expr = getInverseCondition(bool_expr)
            new_postfix_tokens.append(new_bool_expr)
        else:
            raise ValueError('wrong boolean operator %s' % token)

    new_postfix_tokens = list(flattenList(new_postfix_tokens))
    return new_postfix_tokens

def getVariableKeyOperatorValuePairs(tokens):
    variable_key_operator_value_pairs = []
    for token in tokens:
        if isinstance(token, tuple):
            variable_key_operator_value_pairs.append(token)

    return variable_key_operator_value_pairs



if __name__ == '__main__':
    plain_string = '! ( ( window = closed & ! ! door = closed | ( mail = alerted ) ) )'
    infix_tokens = tokenParser(plain_string)
    postfix_tokens = infixToPostfix(infix_tokens)
    print(postfix_tokens)
    postfix_tokens = expandNotOperator(postfix_tokens)
    print(postfix_tokens)
    postfix_tokens.append('!')
    postfix_tokens = expandNotOperator(postfix_tokens)
    print(postfix_tokens)
    print(getVariableValuePairs(postfix_tokens))
