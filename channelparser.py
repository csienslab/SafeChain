#!/usr/bin/python3

import pathlib
import glob
import json
import random
import collections

def checkIfChannelVariablesErrors(channel):
    variables = channel['variables']

    for variable_name, variable in variables.items():
        if 'type' not in variable:
            raise ValueError('[%s] undefined type' % variable_name)

        if variable['type'] not in ['boolean', 'set', 'range']:
            raise ValueError('[%s] unsupported type' % variable_name)

        if variable['type'] == 'set' and ('valueSet' not in variable or len(variable['valueSet']) == 0):
            raise ValueError('[%s] undefined or empty value set' % variable_name)

        if variable['type'] == 'range' and ('minValue' not in variable or 'maxValue' not in variable):
            raise ValueError('[%s] undefined value range' % variable_name)

def checkIfChannelActionsErrors(channel):
    if 'actions' not in channel:
        return

    for action_name, actions in channel['actions'].items():
        for action in actions:
            action_variable_name = action['variable']
            if action_variable_name not in channel['variables']:
                raise ValueError('[%s] variable %s is not defined' % (action_name, action_variable_name))

            action_variable = channel['variables'][action_variable_name]
            if action_variable['type'] == 'boolean':
                if action['value'] == '!' or action['value'] == 'FALSE' or action['value'] == 'TRUE':
                    continue
                else:
                    raise ValueError('[%s] action_variable %s is illegal' % (action_name, action_variable_name))

            elif action_variable['type'] == 'set':
                if (action['value'] == '*' or action['value'] == '?') and set(action['valueSet']) <= set(action_variable['valueSet']):
                    continue
                elif action['value'] == '!' and len(action_variable['valueSet']) == 2:
                    continue
                elif (action['value'] != '*' and action['value'] != '?' and action['value'] != '!') and \
                        action['value'] in action_variable['valueSet']:
                    continue
                else:
                    raise ValueError('[%s] action_variable %s is illegal' % (action_name, action_variable_name))

            elif action_variable['type'] == 'range':
                if (action['value'] == '*' or action['value'] == '?') and \
                   (action['minValue'] >= action_variable['minValue'] and action['minValue'] <= action_variable['maxValue']) and \
                   (action['maxValue'] >= action_variable['minValue'] and action['maxValue'] <= action_variable['maxValue']):
                       continue
                elif (action['value'] != '*' and action['value'] != '?') and \
                     isinstance(action['value'], int) and\
                     (action['value'] >= action_variable['minValue'] and action['value'] <= action_variable['maxValue']):
                         continue
                else:
                    raise ValueError('[%s] action_variable %s is illegal' % (action_name, action_variable_name))


def checkChannelTrigger(channel, trigger_name, trigger):
    if 'relationalOperator' in trigger:
        trigger_variable_name = trigger['variable']
        if trigger_variable_name not in channel['variables']:
            raise ValueError('[%s] variable %s is not defined' % (trigger_name, trigger_variable_name))

        trigger_variable = channel['variables'][trigger_variable_name]
        if trigger_variable['type'] == 'boolean':
            if trigger['value'] != 'FALSE' and trigger['value'] != 'TRUE':
                raise ValueError('[%s] trigger_variable %s target value is illegal' % (trigger_name, trigger_variable_name))
            elif trigger['relationalOperator'] != '=' and trigger['relationalOperator'] != '!=':
                raise ValueError('[%s] trigger_variable %s relational operator is illegal' % (trigger_name, trigger_variable_name))
            else:
                return

        elif trigger_variable['type'] == 'set':
            if trigger['relationalOperator'] != '=' and trigger['relationalOperator'] != '!=':
                raise ValueError('[%s] trigger_variable %s relational operator is illegal' % (trigger_name, trigger_variable_name))
            elif trigger['value'] == '*' and set(trigger['valueSet']) <= set(trigger_variable['valueSet']):
                return
            elif trigger['value'] != '*' and trigger['value'] in trigger_variable['valueSet']:
                return
            else:
                raise ValueError('[%s] trigger_variable %s is illegal' % (trigger_name, trigger_variable_name))

        elif trigger_variable['type'] == 'range':
            if trigger['value'] == '*' and \
               (trigger['minValue'] >= trigger_variable['minValue'] and trigger['minValue'] <= trigger_variable['maxValue']) and \
               (trigger['maxValue'] >= trigger_variable['minValue'] and trigger['maxValue'] <= trigger_variable['maxValue']):
                   return
            elif trigger['value'] != '*' and isinstance(trigger['value'], int) and \
                 (trigger['value'] >= trigger_variable['minValue'] and trigger['value'] <= trigger_variable['maxValue']):
                     return
            else:
                raise ValueError('[%s] trigger_variable %s is illegal' % (trigger_name, trigger_variable_name))

    elif 'logicalOperator' in trigger:
        for operand in trigger['operand']:
            checkChannelTrigger(channel, trigger_name, operand)
    else:
        raise ValueError('trigger %s is not defined well' % trigger_name)

def checkIfChannelTriggersErrors(channel):
    if 'triggers' not in channel:
        return

    for trigger_name, trigger in channel['triggers'].items():
        checkChannelTrigger(channel, trigger_name, trigger)

def extractTriggerVariables(trigger):
    if 'relationalOperator' in trigger:
        return set([trigger['variable']])

    var = set()
    for operand in trigger['operand']:
        var |= extractTriggerVariables(operand)
    return var

def isTriggerWithInput(trigger):
    if 'relationalOperator' in trigger:
        return trigger['value'] == '*'

    for operand in trigger['operand']:
        if isTriggerWithInput(operand):
            return True
    return False

def extractTriggersInformation(channel):
    triggers = collections.defaultdict(dict)
    for trigger_name, trigger in channel['triggers'].items():
        triggers[trigger_name]['trigger'] = trigger
        triggers[trigger_name]['variables'] = list(extractTriggerVariables(trigger))
        triggers[trigger_name]['input'] = isTriggerWithInput(trigger)
    channel['triggers'] = triggers

def extractActionVariables(action):
    return set(act['variable'] for act in action)

def isActionWithInput(action):
    for act in action:
        if act['value'] == '*':
            return True
    return False

def extractActionsInformation(channel):
    actions = collections.defaultdict(dict)
    for action_name, action in channel['actions'].items():
        actions[action_name]['action'] = action
        actions[action_name]['variables'] = list(extractActionVariables(action))
        actions[action_name]['input'] = isActionWithInput(action)
    channel['actions'] = actions

def loadChannelFromFile(filepath):
    if isinstance(filepath, str):
        path = pathlib.Path(filepath)
    elif isinstance(filepath, pathlib.Path):
        path = filepath
    else:
        raise ValueError('type(filepath) is only supported in str or pathlib.Path')

    with path.open() as f:
        channel = json.load(f)

    if 'actions' in channel:
        channel['actions'] = dict((path.stem + ': ' + action_name, action)for action_name, action in channel['actions'].items())
    else:
        channel['actions'] = dict()

    if 'triggers' in channel:
        channel['triggers'] = dict((path.stem + ': ' + trigger_name, trigger)for trigger_name, trigger in channel['triggers'].items())
    else:
        channel['triggers'] = dict()

    return channel


def loadChannelFromFiles(filepaths):
    channels = collections.defaultdict(dict)

    for filepath in filepaths:
        channel = loadChannelFromFile(filepath)
        channels['variables'].update(channel['variables'])
        channels['actions'].update(channel['actions'])
        channels['triggers'].update(channel['triggers'])

    return channels


def loadChannelsFromDirectory(directory_path):
    path = pathlib.Path(directory_path)
    filepaths = path.glob('*.json')
    channels = loadChannelFromFiles(filepaths)

    checkIfChannelVariablesErrors(channels)
    checkIfChannelActionsErrors(channels)
    checkIfChannelTriggersErrors(channels)

    extractTriggersInformation(channels)
    extractActionsInformation(channels)

    return channels

if __name__ == '__main__':
    channel = loadChannelsFromDirectory('./channels')
