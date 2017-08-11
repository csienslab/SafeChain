#!/usr/bin/env python3

import argparse
import json
import collections
import functools
import operator
import pathlib
import pickle
import math

def is_dir(dirname):
    """Check if a path is an actual directory"""
    path = pathlib.Path(dirname)
    if not path.is_dir():
        msg = '{0} is not a directory'.format(dirname)
        raise argparse.ArgumentTypeError(msg)

    return dirname

def extract(args):
    # Constant index
    TRIGGER_CHANNEL_IDX = 5
    TRIGGER_IDX = 6
    ACTION_CHANNEL_IDX = 8
    ACTION_IDX = 9

    # set up the variable to store data, which is a dict of dict of dict
    channels = collections.defaultdict(functools.partial(collections.defaultdict, dict))
    itemgetter = operator.itemgetter(TRIGGER_CHANNEL_IDX, TRIGGER_IDX, ACTION_CHANNEL_IDX, ACTION_IDX)

    # accumlate the triggers and actions for each channel
    with args.input as f:
        for line in f:
            line = line.strip()
            columns = line.split('\t')

            trigger_channel, trigger, action_channel, action = itemgetter(columns)

            channels[trigger_channel]['triggers'][trigger] = {}
            channels[trigger_channel]['variables'] = {}

            channels[action_channel]['actions'][action] = {}
            channels[action_channel]['variables'] = {}

    # for each channel, write its data into file.json
    for channel in channels:
        filename = '{}.json.todo'.format(channel)
        path = pathlib.Path(args.output_directory, filename)
        with path.open(mode='w', encoding='UTF-8') as f:
            f.write(json.dumps(channels[channel], sort_keys=True, indent=2))

def generate(args):
    channels = dict()

    # find all possible defined channels
    path = pathlib.Path(args.input_directory)
    filepaths = path.glob('*.json')

    for filepath in filepaths:
        channel_name = filepath.stem
        with filepath.open() as f:
            channel_content = json.load(f)

        channels[channel_name] = channel_content

    # dump the customized dataset
    with args.output as f:
        pickle.dump(channels, f, protocol=pickle.HIGHEST_PROTOCOL)

def count(args):
    channels = dict()

    # find all possible defined channels
    path = pathlib.Path(args.input_directory)
    filepaths = path.glob('*.json')

    channels_count = 0
    variables_count = 0
    variables_size = 1

    for filepath in filepaths:
        channels_count += 1
        channel_name = filepath.stem
        with filepath.open() as f:
            channel_content = json.load(f)

        variables_count += len(channel_content['variables'])
        for variable_name, variable in channel_content['variables'].items():
            if variable['type'] == 'boolean':
                variables_size *= 2
            elif variable['type'] == 'set':
                variables_size *= len(variable['setValue'])
            elif variable['type'] == 'range':
                variables_size *= variable['maxValue'] - variable['minValue'] + 1
            else:
                raise ValueError('Unknown type: {}'.format(variable['type']))

    print('Number of channels: {}'.format(channels_count))
    print('Number of variables: {}'.format(variables_count))
    print('Number of possible states: 2^{}'.format(math.log2(variables_size)))

if __name__ == '__main__':
    # set up the top level parser
    parser = argparse.ArgumentParser(description='A program written to handle the dataset')
    subparsers = parser.add_subparsers()

    # set up the second level parser for extract
    parser_extract = subparsers.add_parser('extract', help='extract the channels from dataset')
    parser_extract.add_argument('-i', '--input', required=True, type=argparse.FileType('r'), help='the file of dataset')
    parser_extract.add_argument('-o', '--output_directory', required=True, type=is_dir, help='the directory to save extracted channels')
    parser_extract.set_defaults(func=extract)

    parser_generator = subparsers.add_parser('generate', help='check the defined channels and generate the custom dataset')
    parser_generator.add_argument('-i', '--input_directory', required=True, type=is_dir, help='the directory of defined channels')
    parser_generator.add_argument('-o', '--output', required=True, type=argparse.FileType('wb'), help='the file to save custom dataset')
    parser_generator.set_defaults(func=generate)

    parser_count = subparsers.add_parser('count', help='analyze the channels from dataset')
    parser_count.add_argument('-i', '--input_directory', required=True, type=is_dir, help='the directory of defined channels')
    parser_count.set_defaults(func=count)

    # parse the command line and call the associated function
    args = parser.parse_args()
    args.func(args)
