#!/usr/bin/python3

import argparse
import subprocess

from converter import NuSMVConverter

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='IFTTT rule checking')
    parser.add_argument('-i', '--input', type=str, required=True, help='the rule set from www.upod.io')
    parser.add_argument('-s', '--script', type=str, required=True, help='the generated script file')
    parser.add_argument('--policy', type=str, help='the policy to check with NuSMV (boolean format)')
    parser.add_argument('--compromised', type=str, nargs='+', help='the compromised devices')
    parser.add_argument('--pruning', action='store_true', help='whether to prune rules')
    parser.add_argument('--grouping', action='store_true', help='whether to group equivalent variable rules')
    parser.add_argument('--validate', action='store_true', help='validate policy with NuSMV')
    args = parser.parse_args()

    converter = NuSMVConverter('./channels/')

    TRIGGER_CHANNEL_IDX = 5
    TRIGGER_IDX = 6
    ACTION_CHANNEL_IDX = 8
    ACTION_IDX = 9

    with open(args.input, mode='r', encoding='UTF-8') as f:
        for line in f:
            line = line.strip()
            columns = line.split('\t')

            trigger_channel_name = columns[TRIGGER_CHANNEL_IDX]
            trigger_name = columns[TRIGGER_IDX]
            action_channel_name = columns[ACTION_CHANNEL_IDX]
            action_name = columns[ACTION_IDX]

            if converter.isConvertibleRule(trigger_channel_name, trigger_name, action_channel_name, action_name):
                converter.addRule(trigger_channel_name, trigger_name, action_channel_name, action_name)


    if args.compromised:
        for channel in args.compromised:
            converter.addCompromisedChannel(channel)

    converter.constraint = args.policy

    converter.dump(args.script, pruning=args.pruning, grouping=args.grouping)

    if args.validate:
        p = subprocess.Popen(['NuSMV', args.script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()

        print(out.decode('UTF-8'))

