#!/usr/bin/python3

import pathlib
import glob
import json
import random

def checkChannelVariablesErrors(channel_name, channel):
    variables = channel['variables']

    for variable_name in variables:
        variable = variables[variable_name]
        if 'type' not in variable:
            raise ValueError('[%s] (%s) undefined type' % (channel_name, variable_name))

        if variable['type'] not in ['set', 'range']:
            raise ValueError('[%s] (%s) unsupported type' % (channel_name, variable_name))

        if variable['type'] == 'set' and ('value' not in variable or len(variable['value']) == 0):
            raise ValueError('[%s] (%s) undefined or empty set' % (channel_name, variable_name))

        if variable['type'] == 'range' and ('minValue' not in variable or 'maxValue' not in variable):
            raise ValueError('[%s] (%s) undefined value range' % (channel_name, variable_name))

def checkChannelActionsErrors(channel):
    if 'actions' not in channel:
        return

    actions = channel['actions']
    variables = channel['variables']

    for action_name in actions:
        for action in actions[action_name]:
            if action['variable'] in variables:
                if variables[action['variable']]['type'] == 'set':
                    if (action['value'] == '*' or action['value'] == '?') and \
                       set(action['valueSet']) < set(variables[action['variable']]['range']):
                           continue
                    elif (action['value'] != '*' and action['value'] != '?') and \
                         action['value'] in variables[action['variable']]['value']:
                             continue
                elif variables[action['variable']]['type'] == 'range':
                    if (action['value'] == '*' or action['value'] == '?') and \
                       (action['minValue'] >= variables[action['variable']]['minValue'] and action['minValue'] <= variables[action['variable']]['maxValue']) and \
                       (action['maxValue'] >= variables[action['variable']]['minValue'] and action['maxValue'] <= variables[action['variable']]['maxValue']):
                           continue
                    elif (action['value'] != '*' and action['value'] != '?') and \
                         action['value'] >= variables[action['variable']]['minValue'] and action['value'] <= variables[action['variable']]['maxValue']:
                             continue

            raise ValueError('action %s is not defined well' % (action_name))

def checkChannelTrigger(channel, trigger_name, trigger):
    if 'relationalOperator' in trigger:
        if trigger['value'] == '*':
            if channel['variables'][trigger['variable']]['type'] == 'set':
                value = random.choice(trigger['valueSet'])
            elif channel['variables'][trigger['variable']]['type'] == 'range':
                value = str(random.randint(trigger['minValue'], trigger['maxValue']))
            else:
                raise ValueError('trigger %s is not defined well' % trigger_name)
        else:
            value = trigger['value']

        return ' %s %s %s ' % (trigger['variable'], trigger['relationalOperator'], value)
    elif 'logicalOperator' in trigger:
        return trigger['logicalOperator'].join(checkChannelTrigger(channel, trigger_name, operand) for operand in trigger['operand'])
    else:
        raise ValueError('trigger %s is not defined well' % trigger_name)

def checkChannelTriggersErrors(channel):
    if 'triggers' not in channel:
        return

    triggers = channel['triggers']
    for trigger_name in triggers:
        trigger = triggers[trigger_name]
        checkChannelTrigger(channel, trigger_name, trigger)

def checkChannelErrors(channel_name, channel):
    checkChannelVariablesErrors(channel_name, channel)
    checkChannelActionsErrors(channel)
    checkChannelTriggersErrors(channel)


def loadChannelFromFile(purepath):
    with purepath.open() as f:
        channel = json.load(f)

    checkChannelErrors(purepath.stem, channel)
    return channel


def loadChannelsFromDirectory(directory_path):
    channels = {}
    variables = {}

    path = pathlib.Path(directory_path)
    files = path.glob('*.json')
    for f in files:
        channel = loadChannelFromFile(f)
        channels[f.stem] = {}
        if 'triggers' in channel:
            channels[f.stem]['triggers'] = channel['triggers']
        if 'actions' in channel:
            channels[f.stem]['actions'] = channel['actions']
        variables.update(channel['variables'])

    return (channels, variables)

if __name__ == '__main__':
    channels, variables = loadChannelsFromDirectory('./channels/')
