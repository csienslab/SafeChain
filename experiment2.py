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
import numpy
import pprint

import Controller as MyController
import Device as MyDevice

import SimpleLTLPolicy as MySimpleLTLPolicy
import SimpleCTLPolicy as MySimpleCTLPolicy
import InvariantPolicy as MyInvariantPolicy
import PrivacyPolicy as MyPrivacyPolicy

def buildRandomSetting(database, available_rules, number_of_involved_variables, number_of_vulnerable_variables):
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
    current_rules = random.sample(available_rules, 500)
    for count, rule in enumerate(current_rules, start=1):
        trigger_channel_name, trigger_name, action_channel_name, action_name = rule

        rule_name = 'RULE{}'.format(count)
        trigger_inputs = controller.getFeasibleInputsForTrigger(trigger_channel_name, trigger_name)
        action_inputs = controller.getFeasibleInputsForAction(action_channel_name, action_name)
        controller.addRule(rule_name, trigger_channel_name, trigger_name, trigger_inputs, action_channel_name, action_name, action_inputs)

    # random choose vulnerables
    vulnerable_device_variables = random.sample(controller.device_variables, number_of_vulnerable_variables)
    for vulnerable_device_variable in vulnerable_device_variables:
        controller.addVulnerableDeviceVariable(*vulnerable_device_variable)

    device_variables = tuple(controller.device_variables - set(vulnerable_device_variables))
    if len(device_variables) == 0:
        device_variables = tuple(controller.device_variables)

    # random build linear temporal logic policy
    selected_variables = random.sample(set(device_variables), number_of_involved_variables)
    policy_strings = []
    for device_name, variable_name in selected_variables:
        device = controller.getDevice(device_name)
        variable = device.getVariable(variable_name)
        value = random.choice(tuple(variable.getPossibleValues()))
        policy_strings.append('( {0}.{1} != {2} | {0}.{1} = {2} )'.format(device_name, variable_name, value))

    policy_strings = ' & '.join(policy_strings)
    policy = MySimpleLTLPolicy.LTLPolicy(policy_strings)

    # random build computational tree logic
    # selected_variables = random.sample(set(device_variables), number_of_involved_variables)
    # policy_strings = []
    # for device_name, variable_name in selected_variables:
    #     device = controller.getDevice(device_name)
    #     variable = device.getVariable(variable_name)
    #     value = random.choice(tuple(variable.getPossibleValues()))
    #     policy_strings.append('( {0}.{1} != {2} | {0}.{1} = {2} )'.format(device_name, variable_name, value))

    # policy_strings = ' & '.join(policy_strings)
    # policy = MySimpleCTLPolicy.CTLPolicy(policy_strings)

    # random build privacy policy
    # selected_variables = random.sample(set(device_variables), number_of_involved_variables)
    # policy = MyPrivacyPolicy.PrivacyPolicy(set(selected_variables))

    return controller, policy

def checkModel(setting):
    database = copy.deepcopy(setting['database'])
    available_rules = copy.deepcopy(setting['available_rules'])
    number_of_involved_variables = setting['number_of_involved_variables']
    number_of_vulnerable_variables = setting['number_of_vulnerable_variables']
    timeout = setting['timeout']

    controller, policy = buildRandomSetting(database, available_rules, number_of_involved_variables, number_of_vulnerable_variables)
    optimized_filename, optimized_result, *optimized_time = controller.check(policy, grouping=True, pruning=True, timeout=timeout)

    return number_of_involved_variables, number_of_vulnerable_variables, optimized_filename, optimized_result, optimized_time

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', type=str, required=True, help='the prefix name of result files')
    parser.add_argument('--number_of_trials', type=int, required=True, help='the number of trials')
    parser.add_argument('--min_number_of_vulnerable_variables', type=int, required=True, help='the number of minimum vulnerable variables')
    parser.add_argument('--max_number_of_vulnerable_variables', type=int, required=True, help='the number of maximum vulnerable variables')
    parser.add_argument('--min_number_of_involved_variables', type=int, required=True, help='the number of minimum involved variables')
    parser.add_argument('--max_number_of_involved_variables', type=int, required=True, help='the number of maximum involved variables')
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

    length_x = len(range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1))
    length_y = len(range(args.min_number_of_vulnerable_variables, args.max_number_of_vulnerable_variables + 1))
    times = [[0] * length_x for i in range(length_y)]

    settings = [{'database': database,
                 'available_rules': available_rules,
                 'number_of_vulnerable_variables': number_of_vulnerable_variables,
                 'number_of_involved_variables': number_of_involved_variables,
                 'timeout': args.timeout}
                for number_of_involved_variables in range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1)
                for number_of_vulnerable_variables in range(args.min_number_of_vulnerable_variables, args.max_number_of_vulnerable_variables + 1)
                for i in range(args.number_of_trials)]

    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        for number_of_involved_variables, number_of_vulnerable_variables, optimized_filename, optimized_result, optimized_time in executor.map(checkModel, reversed(settings)):
            y = number_of_vulnerable_variables - args.min_number_of_vulnerable_variables
            x = number_of_involved_variables - args.min_number_of_involved_variables
            times[y][x] += sum(optimized_time)

    for i in range(length_y):
        for j in range(length_x):
            times[i][j] /= args.number_of_trials

    print('End Time: {0}'.format(datetime.datetime.now()))

    filename = '{}.pickle'.format(args.prefix)
    with open(filename, 'wb') as f:
        pickle.dump(times, f, pickle.HIGHEST_PROTOCOL)

    plt.pcolor(times, cmap=plt.cm.gray)
    plt.colorbar()

    ticks = [i + 0.5 for i in range(length_x)]
    labels = [number_of_involved_variables for number_of_involved_variables in range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1)]
    plt.xticks(ticks, labels)
    plt.xlabel('Number of policy attributes')

    ticks = [i + 0.5 for i in range(length_y)]
    labels = [number_of_vulnerable_variables for number_of_vulnerable_variables in range(args.min_number_of_vulnerable_variables, args.max_number_of_vulnerable_variables + 1)]
    plt.yticks(ticks, labels)
    plt.ylabel('Number of vulnerable attributes')

    plt.savefig('{}.pdf'.format(args.prefix), bbox_inches='tight', pad_inches=0.0)

    # # # bar plot
    # # plt.figure()
    # # fig, ax = plt.subplots()

    # # width = 0.35
    # # N = len(range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1))
    # # ind = numpy.arange(N)
    # # means = tuple(times[i] / args.number_of_trials for i in range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1))
    # # rects2 = ax.bar(ind, means, width, color='white', edgecolor='black')

    # # ax.set_ylabel('Time (s)')
    # # ax.set_xlabel('Number of involved attributes')
    # # ax.set_xticks(ind)
    # # ax.set_xticklabels(tuple(number_of_involved_variables for number_of_involved_variables in range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1)))
    # # ax.set_ylim([0.0, 0.47])

    # # plt.savefig('{}_bar.pdf'.format(args.prefix))

    # combine
    # ltl_involved = [0.25365368663950355, 0.26063656428456305, 0.267161798490677, 0.27565117092919533, 0.2791417625482427, 0.28872311575745696, 0.29284934558637904, 0.3054807201845105]
    # ltl_vul = [0.24499574801605195, 0.24331209252669941, 0.2453710427331971, 0.24166468772583174, 0.24492531419021543, 0.24472656678385102, 0.2475413429053733, 0.2446847415717784]
    # ltl = [0.2531554289571941, 0.2597162900469266, 0.2665056884372607, 0.2711737535946304, 0.2788549713541288, 0.28552776352642106, 0.28749038162932267, 0.290235062427935]

    # privacy_low = [0.25096660371113105, 0.33137132282566745, 0.3686613266840577, 0.35160185593611093, 0.3351248218662804, 0.39247665092884565, 0.5234499153528596, 0.466502586865448]
    # privacy_high = [0.28042805001465604, 0.27640242033218965, 0.33214549170271496, 0.2906605389547767, 0.4282733426771592, 0.41732891176780684, 0.4501022307664389, 0.4395960046324180]
    # privacy = [0.22616610003518872, 0.30766856458608527, 0.33368308620061726, 0.5370068732524523, 0.804538099961821, 1.9853007950345054, 2.484106618011021, 4.558633163855528]

    # first = [0.24499574801605195, 0.24331209252669941, 0.2453710427331971, 0.24166468772583174, 0.24492531419021543, 0.24472656678385102, 0.2475413429053733, 0.2446847415717784]
    # second = [0.25365368663950355, 0.26063656428456305, 0.267161798490677, 0.27565117092919533, 0.2791417625482427, 0.28872311575745696, 0.29284934558637904, 0.3054807201845105]
    # third = [0.2531554289571941, 0.2597162900469266, 0.2665056884372607, 0.2711737535946304, 0.2788549713541288, 0.28552776352642106, 0.28749038162932267, 0.290235062427935]

    # bar plot
    # plt.figure()
    # fig, ax = plt.subplots()

    # width = 0.25
    # N = len(range(1, 8 + 1))
    # ind = numpy.arange(N)
    # means = tuple(first)
    # rects1 = ax.bar(ind, means, width, color='white', edgecolor='black')
    # means = tuple(second)
    # rects2 = ax.bar(ind + width, means, width, color='white', edgecolor='black', hatch='...')
    # means = tuple(third)
    # rects3 = ax.bar(ind + width + width, means, width, color='white', edgecolor='black', hatch='xxxxxx')

    # ax.set_ylabel('Time (s)')
    # ax.set_xlabel('X')
    # ax.set_xticks(ind + width)
    # ax.set_xticklabels(tuple(number_of_rules for number_of_rules in range(1, 8 + 1)))
    # ax.legend((rects1[0], rects2[0], rects3[0]), ('1 policy attributes vs X vulnerable attributes', 'X policy attributes vs 1 vulnerable attributes', 'X policy attributes vs X vulnerable attributes'), ncol=1, frameon=False, loc='upper left')
    # ax.set_ylim([0.0, 0.5])

    # plt.savefig('{}_bar.pdf'.format('ltl_attributes'), bbox_inches='tight', pad_inches=0.0)






