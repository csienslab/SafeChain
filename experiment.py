#!/usr/bin/env python3

import pickle
import random
import re
import pprint
import operator
import os
import concurrent.futures

import Controller as MyController
import Device as MyDevice

import SimpleLTLPolicy as MySimpleLTLPolicy
import InvariantPolicy as MyInvariantPolicy

def buildRandomLTLSetting(database, available_rules, number_of_rules):
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

    # random choose vulnerables
    device_name = random.choice(tuple(controller.devices))
    controller.addVulnerableDevice(device_name)

    # random build invariant policy
    device_name, variable_name = random.choice(tuple(controller.device_variables))
    device = controller.getDevice(device_name)
    variable = device.getVariable(variable_name)
    value = random.choice(tuple(variable.getPossibleValues()))
    policy = MySimpleLTLPolicy.LTLPolicy('{0}.{1} != {2} | {0}.{1} = {2}'.format(device_name, variable_name, value))

    return {'controller': controller, 'policy': policy}

def checkModel(setting):
    controller = setting['controller']
    policy = setting['policy']
    grouping = setting['grouping']
    pruning = setting['pruning']
    return controller.check(policy, grouping=grouping, pruning=pruning)

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
        print('{0:>6} {1:>15} {2:>15} {3:>15} {4:>15}'.format(number_of_rules, 'grouping', 'pruning', 'parsing', 'checking'))
        settings = [buildRandomLTLSetting(database, available_rules, number_of_rules) for i in range(number_of_trials)]

        for grouping, pruning in [(False, False), (True, True)]:
            grouping_times = list()
            pruning_times = list()
            parsing_times = list()
            checking_times = list()

            for setting in settings:
                setting['grouping'] = grouping
                setting['pruning'] = pruning

            with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
                for result, grouping_time, pruning_time, parsing_time, checking_time in executor.map(checkModel, settings):
                    grouping_times.append(grouping_time)
                    pruning_times.append(pruning_time)
                    parsing_times.append(parsing_time)
                    checking_times.append(checking_time)

            grouping_time = sum(grouping_times) / number_of_trials
            pruning_time = sum(pruning_times) / number_of_trials
            parsing_time = sum(parsing_times) / number_of_trials
            checking_time = sum(checking_times) / number_of_trials
            overtime = sum(checking_time > 3600 for checking_time in checking_times)

            print('{0:^6} {1:15f} {2:15f} {3:15f} {4:15f} ({5})'.format('', grouping_time, pruning_time, parsing_time, checking_time, overtime))

