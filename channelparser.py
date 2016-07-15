#!/usr/bin/python3

import pathlib
import glob
import json

from ifttt import Variable, Trigger, Action

def loadChannelFromFile(filepath):
    if isinstance(filepath, str):
        path = pathlib.Path(filepath)
    elif isinstance(filepath, pathlib.Path):
        path = filepath
    else:
        raise ValueError('type(filepath) is only supported in str or pathlib.Path')

    with path.open() as f:
        channel = json.load(f)

    if 'actions' not in channel:
        channel['actions'] = dict()

    if 'triggers' not in channel:
        channel['triggers'] = dict()

    return channel


def loadChannelFromFiles(filepaths):
    variables = dict()
    triggers = dict()
    actions = dict()

    for filepath in filepaths:
        channel = loadChannelFromFile(filepath)
        channel_name = filepath.stem

        for variable_name, variable_content in channel['variables'].items():
            Variable.checkErrors(channel_name, variable_name, variable_content)

            variable = Variable(channel_name, variable_name, variable_content)
            variable_key = Variable.getUniqueName(channel_name, variable_name)
            variables[variable_key] = variable

        for trigger_name, trigger_content in channel['triggers'].items():
            Trigger.checkErrors(channel_name, trigger_name, trigger_content, variables)

            trigger_key = Trigger.getUniqueName(channel_name, trigger_name)
            triggers[trigger_key] = trigger_content

        for action_name, action_content in channel['actions'].items():
            Action.checkErrors(channel_name, action_name, action_content, variables)

            action_key = Action.getUniqueName(channel_name, action_name)
            actions[action_key] = action_content

    return {'variables': variables, 'triggers': triggers, 'actions': actions}


def loadChannelsFromDirectory(directory_path):
    path = pathlib.Path(directory_path)
    filepaths = path.glob('*.json')
    channels = loadChannelFromFiles(filepaths)

    return channels


if __name__ == '__main__':
    channels = loadChannelsFromDirectory('channels')

