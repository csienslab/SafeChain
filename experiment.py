#!/usr/bin/env python3

import pickle
import random
import re
import pprint
import operator
import os

import Controller as MyController
import Device as MyDevice

import SimpleLTLPolicy as MySimpleLTLPolicy
import InvariantPolicy as MyInvariantPolicy

if __name__ == '__main__':
    # show information
    print('Current PID: {0}'.format(os.getpid()))

    # load database
    with open('database.dat', 'rb') as f:
        database = pickle.load(f)

    # get available rules
    controller = MyController.Controller(database)
    available_rules = list()
    with open('dataset/coreresultsMay16.tsv', 'r') as f:
        all_channels = controller.database.keys()
        itemgetter = operator.itemgetter(5, 6, 8, 9)
        for line in f:
            line = line.strip()
            columns = line.split('\t')
            trigger_channel_name, trigger_name, action_channel_name, action_name = itemgetter(columns)
            if trigger_channel_name in all_channels and action_channel_name in all_channels:
                available_rules.append((trigger_channel_name, trigger_name, action_channel_name, action_name))

    number_of_trials = 100
    for number_of_rules in range(25, 1001, 25):
        original = (0, 0, 0, 0)
        optimized = (0, 0, 0, 0)
        original_overtime = 0
        optimized_overtime = 0
        for trial in range(number_of_trials):
            # initial controller
            controller = MyController.Controller(database)

            # add devices
            for channel_name, channel_definition in controller.getFeasibleDevices():
                name = re.sub('[^A-Za-z0-9_]+', '', channel_name).lower()
                device = MyDevice.Device(channel_name, channel_definition, name)

                possible_values_of_variables = device.getPossibleValuesOfVariables()
                state = dict((variable_name, random.choice(tuple(possible_values))) for variable_name, possible_values in possible_values_of_variables.items())
                device.setState(state)

                controller.addDevice(device)

            # add rules
            current_rules = random.sample(available_rules, number_of_rules)
            for count, rule in enumerate(current_rules, start=1):
                trigger_channel_name, trigger_name, action_channel_name, action_name = rule

                rule_name = 'RULE{}'.format(count)
                trigger_inputs = controller.getFeasibleInputsForTrigger(trigger_channel_name, trigger_name)
                action_inputs = controller.getFeasibleInputsForAction(action_channel_name, action_name)
                controller.addRule(rule_name, trigger_channel_name, trigger_name, trigger_inputs, action_channel_name, action_name, action_inputs)

            # random choose vulnerable
            device_name = random.choice(tuple(controller.devices))
            controller.addVulnerableDevice(device_name)

            # random build invariant policy
            device_name, variable_name = random.choice(tuple(controller.device_variables))
            device = controller.getDevice(device_name)
            variable = device.getVariable(variable_name)
            value = random.choice(tuple(variable.getPossibleValues()))
            policy = MySimpleLTLPolicy.LTLPolicy('{0}.{1} != {2} | {0}.{1} = {2}'.format(device_name, variable_name, value))

            # print(count)
            result, *time = controller.check(policy, grouping=False, pruning=False)
            original = tuple(map(operator.add, original, time))
            original_overtime += 1 if result == None else 0

            result, *time = controller.check(policy, custom=False, grouping=True, pruning=True)
            optimized = tuple(map(operator.add, optimized, time))
            optimized_overtime += 1 if result == None else 0

        original = tuple(v / number_of_trials for v in original)
        optimized = tuple(v / number_of_trials for v in optimized)
        print('{0:>6} {1:>15} {2:>15} {3:>15} {4:>15}'.format('number', 'grouping', 'pruning', 'parsing', 'checking'))
        print('{0:^6} {1:15f} {2:15f} {3:15f} {4:15f} ({5})'.format(number_of_rules, *original, original_overtime))
        print('{0:^6} {1:15f} {2:15f} {3:15f} {4:15f} ({5})'.format('', *optimized, optimized_overtime))

