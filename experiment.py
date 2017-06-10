#!/usr/bin/env python3

import pickle
import random
import re
import operator
import os
import collections
import datetime
import copy
import statistics
import argparse
import concurrent.futures
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import Controller as MyController
import Device as MyDevice

import SimpleLTLPolicy as MySimpleLTLPolicy
import SimpleCTLPolicy as MySimpleCTLPolicy
import InvariantPolicy as MyInvariantPolicy
import PrivacyPolicy as MyPrivacyPolicy

def buildRandomSetting(database, available_rules, number_of_rules):
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
    vulnerable_device_name = random.choice(tuple(set(device_name for device_name, variable_name in controller.device_variables)))
    controller.addVulnerableDevice(vulnerable_device_name)

    device_variables = tuple((device_name, variable_name) for device_name, variable_name in controller.device_variables if device_name != vulnerable_device_name)
    if len(device_variables) == 0:
        device_variables = tuple((device_name, variable_name) for device_name, variable_name in controller.device_variables)

    # random build linear temporal logic policy
    # device_name, variable_name = random.choice(device_variables)
    # device = controller.getDevice(device_name)
    # variable = device.getVariable(variable_name)
    # value = random.choice(tuple(variable.getPossibleValues()))
    # policy = MySimpleLTLPolicy.LTLPolicy('{0}.{1} != {2} | {0}.{1} = {2}'.format(device_name, variable_name, value))

    # random build computational tree logic
    device_name, variable_name = random.choice(device_variables)
    device = controller.getDevice(device_name)
    variable = device.getVariable(variable_name)
    value = random.choice(tuple(variable.getPossibleValues()))
    policy = MySimpleCTLPolicy.CTLPolicy('{0}.{1} != {2} | {0}.{1} = {2}'.format(device_name, variable_name, value))

    # random build privacy policy
    # device_name, variable_name = random.choice(device_variables)
    # policy = MyPrivacyPolicy.PrivacyPolicy(set([(device_name, variable_name)]))

    return controller, policy

def checkModel(setting):
    database = copy.deepcopy(setting['database'])
    available_rules = copy.deepcopy(setting['available_rules'])
    number_of_rules = setting['number_of_rules']
    timeout = setting['timeout']

    controller, policy = buildRandomSetting(database, available_rules, number_of_rules)
    original_result, *original_time  = controller.check(policy, grouping=False, pruning=False, timeout=timeout)
    optimized_result, *optimized_time = controller.check(policy, grouping=True, pruning=True, custom=False, timeout=timeout)

    return number_of_rules, original_result, original_time, optimized_result, optimized_time

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=str, required=True, help='the prefix name of result files')
    parser.add_argument('--number_of_trials', type=int, required=True, help='the number of trials')
    parser.add_argument('--min_number_of_rules', type=int, required=True, help='the number of minimum rules')
    parser.add_argument('--max_number_of_rules', type=int, required=True, help='the number of maximum rules')
    parser.add_argument('--step_size', type=int, required=True, help='the step size')
    parser.add_argument('--timeout', type=int, required=True, help='the number of timeout')
    args = parser.parse_args()

    # show information
    print('Current PID : {0}'.format(os.getpid()))
    print('Current Time: {0}'.format(datetime.datetime.now()))

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

    original_times = collections.defaultdict(list)
    optimized_times = collections.defaultdict(list)

    settings = [{'database': database, 'available_rules': available_rules, 'number_of_rules': number_of_rules, 'timeout': args.timeout}
                for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules+1, args.step_size)
                for i in range(args.number_of_trials)]

    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as executor:
        for number_of_rules, original_result, original_time, optimized_result, optimized_time in executor.map(checkModel, reversed(settings)):
            original_times[number_of_rules].append(original_time)
            optimized_times[number_of_rules].append(optimized_time)

            if len(original_times[number_of_rules]) != args.number_of_trials:
                continue

            print('{0:>6} {1:>15} {2:>15} {3:>15} {4:>15}'.format(number_of_rules, 'grouping', 'pruning', 'parsing', 'checking'))
            time = tuple(map(statistics.mean, zip(*original_times[number_of_rules])))
            overtime = sum(v[3] >= args.timeout for v in original_times[number_of_rules])
            print('{0:^6} {1:15f} {2:15f} {3:15f} {4:15f} ({5})'.format('', *time, overtime))

            time = tuple(map(statistics.mean, zip(*optimized_times[number_of_rules])))
            overtime = sum(v[3] >= args.timeout for v in optimized_times[number_of_rules])
            print('{0:^6} {1:15f} {2:15f} {3:15f} {4:15f} ({5})'.format('', *time, overtime))

    print('End Time    : {0}'.format(datetime.datetime.now()))

    filename = '{}.pickle'.format(args.prefix)
    with open(filename, 'wb') as f:
        obj = {'original_times': original_times, 'optimized_times': optimized_times}
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

    plt.figure()
    x = tuple(number_of_rules for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size) for i in range(args.number_of_trials))
    y = tuple(original_times[number_of_rules][i][3] for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size) for i in range(args.number_of_trials))
    plt.scatter(x, y, color='r', marker='+', alpha=0.5)

    y = tuple(optimized_times[number_of_rules][i][3] for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size) for i in range(args.number_of_trials))
    plt.scatter(x, y, color='g', marker='o', s=(3,)*len(y), alpha=0.5)

    plt.xlabel('Number of rules')
    plt.ylabel('Time of checking (s)')
    plt.savefig('{}_scatter.png'.format(args.prefix))

    plt.figure()
    x = tuple(number_of_rules for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    y = tuple(statistics.mean(original_times[number_of_rules][i][3] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    plt.plot(x, y, 'r--')

    y = tuple(statistics.mean(optimized_times[number_of_rules][i][3] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    plt.plot(x, y, 'g:')

    plt.xlabel('Number of rules')
    plt.ylabel('Average time of checking (s)')
    plt.savefig('{}_average.png'.format(args.prefix))
