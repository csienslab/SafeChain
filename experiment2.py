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

import Controller as MyController
import Device as MyDevice

import SimpleLTLPolicy as MySimpleLTLPolicy
import SimpleCTLPolicy as MySimpleCTLPolicy
import InvariantPolicy as MyInvariantPolicy
import PrivacyPolicy as MyPrivacyPolicy

def buildRandomSetting(database, available_rules, number_of_involved_variables):
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
    current_rules = random.sample(available_rules, 300)
    for count, rule in enumerate(current_rules, start=1):
        trigger_channel_name, trigger_name, action_channel_name, action_name = rule

        rule_name = 'RULE{}'.format(count)
        trigger_inputs = controller.getFeasibleInputsForTrigger(trigger_channel_name, trigger_name)
        action_inputs = controller.getFeasibleInputsForAction(action_channel_name, action_name)
        controller.addRule(rule_name, trigger_channel_name, trigger_name, trigger_inputs, action_channel_name, action_name, action_inputs)

    # random choose vulnerables
    vulnerable_device_variables = random.sample(controller.device_variables, 1)
    for vulnerable_device_variable in vulnerable_device_variables:
        controller.addVulnerableDeviceVariable(*vulnerable_device_variable)

    device_variables = tuple(controller.device_variables - set(vulnerable_device_variables))
    if len(device_variables) == 0:
        device_variables = tuple(controller.device_variables)

    # random build linear temporal logic policy
    # selected_variables = random.sample(set(device_variables), number_of_involved_variables)
    # policy_strings = []
    # for device_name, variable_name in selected_variables:
    #     device = controller.getDevice(device_name)
    #     variable = device.getVariable(variable_name)
    #     value = random.choice(tuple(variable.getPossibleValues()))
    #     policy_strings.append('( {0}.{1} != {2} | {0}.{1} = {2} )'.format(device_name, variable_name, value))

    # policy_strings = ' & '.join(policy_strings)
    # policy = MySimpleLTLPolicy.LTLPolicy(policy_strings)

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
    selected_variables = random.sample(set(device_variables), number_of_involved_variables)
    policy = MyPrivacyPolicy.PrivacyPolicy(set(selected_variables))

    return controller, policy

def checkModel(setting):
    database = copy.deepcopy(setting['database'])
    available_rules = copy.deepcopy(setting['available_rules'])
    number_of_involved_variables = setting['number_of_involved_variables']
    timeout = setting['timeout']

    controller, policy = buildRandomSetting(database, available_rules, number_of_involved_variables)
    optimized_filename, optimized_result, *optimized_time = controller.check(policy, grouping=True, pruning=True, timeout=timeout)

    return number_of_involved_variables, optimized_filename, optimized_result, optimized_time

if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--prefix', type=str, required=True, help='the prefix name of result files')
    # parser.add_argument('--number_of_trials', type=int, required=True, help='the number of trials')
    # parser.add_argument('--min_number_of_involved_variables', type=int, required=True, help='the number of minimum involved variables')
    # parser.add_argument('--max_number_of_involved_variables', type=int, required=True, help='the number of maximum involved variables')
    # parser.add_argument('--timeout', type=int, required=True, help='the number of timeout')
    # args = parser.parse_args()

    # # load database
    # with open('database.dat', 'rb') as f:
    #     database = pickle.load(f)

    # # get available rules
    # controller = MyController.Controller(database)
    # available_rules = list()
    # with open('dataset/coreresultsMay16.tsv', 'r') as f:
    #     all_channels = controller.database.keys()
    #     itemgetter = operator.itemgetter(5, 6, 8, 9)
    #     for line in f:
    #         line = line.strip()
    #         columns = line.split('\t')
    #         trigger_channel_name, trigger_name, action_channel_name, action_name = itemgetter(columns)
    #         if trigger_channel_name in all_channels and action_channel_name in all_channels:
    #             available_rules.append((trigger_channel_name, trigger_name, action_channel_name, action_name))

    # times = [0] * (args.max_number_of_involved_variables + 1)
    # for number_of_involved_variables in reversed(range(args.min_number_of_involved_variables, args.max_number_of_involved_variables+1)):
    #     for i in range(args.number_of_trials):
    #         settings = {'database': database,
    #                     'available_rules': available_rules,
    #                     'number_of_involved_variables': number_of_involved_variables,
    #                     'timeout': args.timeout}

    #         number_of_involved_variables, optimized_filename, optimized_result, optimized_time = checkModel(settings)

    #         times[number_of_involved_variables] += sum(optimized_time)

    #     print(number_of_involved_variables, times[number_of_involved_variables]/args.number_of_trials)

    # # bar plot
    # plt.figure()
    # fig, ax = plt.subplots()

    # width = 0.35
    # N = len(range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1))
    # ind = numpy.arange(N)
    # means = tuple(times[i] / args.number_of_trials for i in range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1))
    # rects2 = ax.bar(ind, means, width, color='green')

    # ax.set_ylabel('Time (s)')
    # ax.set_xlabel('Number of HIGH attributes')
    # ax.set_xticks(ind)
    # ax.set_xticklabels(tuple(number_of_involved_variables for number_of_involved_variables in range(args.min_number_of_involved_variables, args.max_number_of_involved_variables + 1)))
    # ax.set_ylim([0.0, 0.47])

    # plt.savefig('{}_bar.pdf'.format(args.prefix))

    # combine
    # privacy_low = [0.11833471423509763, 0.11843225607735804, 0.12616776111652142, 0.14268427303963108, 0.16009803567489145, 0.15813483838166575, 0.13681290697859366, 0.16884992225910536]
    # privacy_high = [0.11561460791475837, 0.13454492800723528, 0.12540717617288466, 0.12909040200640448, 0.18905261415813585, 0.14219999366439878, 0.13586823322693817, 0.14380368034937419]
    # privacy = [0.09762248884740984, 0.144058376137109, 0.14108355188858696, 0.2330695218584151, 0.23630439946806292, 0.24219636201887623, 0.36678862595173994, 0.4648272933487897]

    # # bar plot
    # plt.figure()
    # fig, ax = plt.subplots()

    # width = 0.25
    # N = len(range(1, 8 + 1))
    # ind = numpy.arange(N)
    # means = tuple(privacy_low)
    # rects1 = ax.bar(ind, means, width, color='white', edgecolor='black')
    # means = tuple(privacy_high)
    # rects2 = ax.bar(ind + width, means, width, color='white', edgecolor='black', hatch='...')
    # means = tuple(privacy)
    # rects3 = ax.bar(ind + width + width, means, width, color='white', edgecolor='black', hatch='xxxxxx')

    # ax.set_ylabel('Time (s)')
    # ax.set_xlabel('Number of attributes')
    # ax.set_xticks(ind + width)
    # ax.set_xticklabels(tuple(number_of_rules for number_of_rules in range(1, 8 + 1)))
    # ax.legend((rects1[0], rects2[0], rects3[0]), ('Dynamic LOW attributes', 'Dynamic HIGH attributes', 'Dynamic LOW and HIGH attributes'), ncol=1, frameon=False)

    # plt.savefig('{}_bar.pdf'.format('allthree'))






