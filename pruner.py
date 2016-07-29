#!/usr/bin/python3

import networkx

from ifttt import VariableType
import grouper
import booleanparser

def check_int(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()

def getGraphNodeName(variable_key, value):
    return ' : '.join((variable_key, value))

def generateRuleEdges(rule, variables, original_variables):
    for trigger_variable_key, trigger_operator, trigger_valueset in rule.trigger.getVariableKeyOperatorValuePairs(original_variables):
        trigger_variable = variables[trigger_variable_key]
        for trigger_value in trigger_valueset:
            for trigger_set_value in trigger_variable.getEquivalentValueSet(trigger_operator, trigger_value):
                trigger_node_name = getGraphNodeName(trigger_variable_key, trigger_set_value)

                for action_variable_key, action_operator, action_valueset in rule.action.getVariableKeyOperatorValuePairs(original_variables):
                    action_variable = variables[action_variable_key]
                    for action_value in action_valueset:
                        for action_set_value in action_variable.getEquivalentValueSet(action_operator, action_value):
                            action_node_name = getGraphNodeName(action_variable_key, action_set_value)

                            yield (trigger_node_name, action_node_name)

def getTargetNodes(constraint, variables):
    infix_tokens = booleanparser.tokenParser(constraint)
    postfix_tokens = booleanparser.infixToPostfix(infix_tokens)

    postfix_tokens.append('!')
    postfix_tokens = booleanparser.expandNotOperator(postfix_tokens)

    target_nodes = set()
    for variable_key, relational_operator, value in booleanparser.getVariableKeyOperatorValuePairs(postfix_tokens):
        variable = variables[variable_key]

        if check_int(value):
            value = int(value)
        valueset = variable.getEquivalentValueSet(relational_operator, value)

        for value in valueset:
            node_name = getGraphNodeName(variable_key, value)
            target_nodes.add(node_name)

    return target_nodes

def getRelatedRules(variables, rules, constraint):
    if constraint == None:
        return rules

    original_variables = variables
    variables, _, _ = grouper.convertToSetVariables(variables, rules, constraint)

    G = networkx.DiGraph()
    for rule in rules:
        for trigger_node_name, action_node_name in generateRuleEdges(rule, variables, original_variables):
            if trigger_node_name not in G:
                G.add_node(trigger_node_name)

            if action_node_name not in G:
                G.add_node(action_node_name)

            if not G.has_edge(trigger_node_name, action_node_name):
                G.add_edge(trigger_node_name, action_node_name, rules=set())

            G.edge[trigger_node_name][action_node_name]['rules'].add(rule.name)

    print(list(networkx.find_cycle(G, orientation='original')))


    unexplored_node = getTargetNodes(constraint, variables)
    explored_node = set()
    related_rules = set()

    while len(unexplored_node) != 0:
        new_unexplored_node = set()
        for node in unexplored_node:
            if node not in G:
                # the node in constraints may not be in the graph
                continue

            for predecessor in G.predecessors_iter(node):
                related_rules.update(G[predecessor][node]['rules'])

                if predecessor not in explored_node:
                    new_unexplored_node.add(predecessor)

            explored_node.add(node)

        unexplored_node = new_unexplored_node

    related_rules = [rule for rule in rules if rule.name in related_rules]
    return related_rules


def getUncompromisedRules(rules, compromised_channels):
    return [rule for rule in rules if rule.action.channel_name not in compromised_channels]
