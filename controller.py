#!/usr/bin/env python3

import pickle
import collections
import random
import re

import rule as myrule

class Controller:
    def __init__(self, database):
        self.database = database

        self.channels = collections.defaultdict(dict)
        self.rules = dict()

    def genAllPossibleChannels(self):
        return self.database.keys()

    def getRandomStateForChannel(self, channel_name):
        state = dict()
        for variable_name, variable in self.database[channel_name].variables.items():
            variable_value = variable.getPossibleValues()
            state[variable_name] = random.choice(variable_value)

        return state

    def getRandomInputForTrigger(self, channel_name, trigger_name):
        channel = self.database[channel_name]
        devices = list(self.channels[channel_name].keys())
        return channel.getRandomInputForTrigger(trigger_name, devices)

    def getRandomInputForAction(self, channel_name, action_name):
        channel = self.database[channel_name]
        devices = list(self.channels[channel_name].keys())
        return channel.getRandomInputForAction(action_name, devices)

    def addChannel(self, channel, device_name, device_state):
        self.channels[channel][device_name] = device_state

    def addRule(self, rule_name, trigger_channel, trigger_name, trigger_inputs, action_channel, action_name, action_inputs):
        trigger = self.database[trigger_channel].triggers[trigger_name]
        action = self.database[action_channel].actions[action_name]
        rule = myrule.Rule(rule_name, trigger, trigger_inputs, action, action_inputs)

        self.rules[rule_name] = rule

    def toNuSMVformat(self):
        string = ''

        all_devices_name = sorted(set(device_name for devices in self.channels.values() for device_name in devices.keys()))

        for channel_name in sorted(self.channels.keys()):
            channel = self.database[channel_name]
            devices = self.channels[channel_name]

            for device_name in sorted(devices.keys()):
                device_state = devices[device_name]
                string += channel.toNuSMVformat(device_name, device_state, self.rules, all_devices_name)

                string += '\n'

        # main module
        string += 'MODULE main\n'
        string += '  VAR\n'

        # initial each devices
        for channel_name in sorted(self.channels.keys()):
            channel = self.database[channel_name]
            devices = self.channels[channel_name]

            for device_name in sorted(devices.keys()):
                module_name = channel.getModuleName(device_name)
                string += '    {0}: {1}({2});\n'.format(device_name, module_name, ', '.join(all_devices_name))
        string += '\n'

        print(string)



if __name__ == '__main__':
    with open('database.dat', 'rb') as f:
        database = pickle.load(f)

    controller = Controller(database)
    for channel in controller.genAllPossibleChannels():
        state = controller.getRandomStateForChannel(channel)
        name = re.sub('[^A-Za-z0-9_]+', '', channel).lower()
        controller.addChannel(channel, name, state)

    rule_name = 'RULE1'
    trigger_channel = 'Adafruit'
    trigger_name = 'Any new data'
    action_channel = 'WeMo Insight Switch'
    action_name = 'Toggle on/off'

    trigger_inputs = controller.getRandomInputForTrigger(trigger_channel, trigger_name)
    action_inputs = controller.getRandomInputForAction(action_channel, action_name)

    controller.addRule(rule_name, trigger_channel, trigger_name, trigger_inputs, action_channel, action_name, action_inputs)

    rule_name = 'RULE2'
    trigger_channel = 'WeMo Insight Switch'
    trigger_name = 'Switched on'
    action_channel = 'Adafruit'
    action_name = 'Send data to Adafruit IO'

    trigger_inputs = controller.getRandomInputForTrigger(trigger_channel, trigger_name)
    action_inputs = controller.getRandomInputForAction(action_channel, action_name)

    controller.addRule(rule_name, trigger_channel, trigger_name, trigger_inputs, action_channel, action_name, action_inputs)
    controller.toNuSMVformat()
