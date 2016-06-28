#!/usr/bin/env python3

import json
import collections
import functools

TRIGGER_CHANNEL_IDX = 5
TRIGGER_IDX = 6
ACTION_CHANNEL_IDX = 8
ACTION_IDX = 9

IOT_CHANNELS = set(['Automatic', 'BMW Labs', 'Dash', 'Mojio', 'Zubie', 'Amazon Alexa', 'August', 'Bang & Olufsen\'s BeoLink Gateway', 'Caleo', 'Comcast Labs', 'D-Link Motion Sensor', 'D-Link Siren', 'D-Link Smart Plug', 'D-Link Water Sensor', 'Daikin Online Controller', 'Danalock', 'ecobee', 'Emberlight', 'Mi|Home', 'Foobot', 'Garageio', 'GE Appliances Cooking', 'GE Appliances Dishwasher', 'GE Appliances Dryer', 'GE Appliances GeoSpring™', 'GE Appliances Refrigerator', 'GE Appliances Washer', 'Gogogate', 'GreenIQ', 'Greenwave Systems', 'Harmony', 'HomeSeer', 'Honeywell evohome', 'Honeywell Lyric', 'Honeywell Single-zone Thermostat', 'Honeywell Total Connect Comfort', 'HP Print', 'Hunter Douglas PowerView', 'IntesisHome', 'Komfy Switch with Camera', 'LaMetric', 'Leeo', 'LG Dryer', 'LG Washer', 'LIFX', 'LightwaveRF Events', 'LightwaveRF Heating', 'LightwaveRF Lighting', 'LightwaveRF Power', 'Lutron Caséta Wireless', 'microBees', 'Musaic', 'myStrom', 'Nefit Easy', 'Nest Protect', 'Nest Thermostat', 'Netatmo Thermostat', 'Netatmo Weather Station', 'Neurio', 'OnHub', 'Parrot Flower Power', 'Philips Hue', 'Qblinks Qmote', 'Rachio', 'RainMachine', 'Roost Smart Battery', 'Samsung Air Purifier', 'Samsung Floor Air Conditioner', 'Samsung Refrigerator', 'Samsung Robot Vacuum', 'Samsung Room Air Conditioner', 'Samsung Washer', 'Sen.se Mother', 'Sensibo', 'simplehuman', 'Skylark', 'Smappee', 'SmartThings', 'Stack Lighting', 'tadoº Smart AC Control', 'tadoº Smart Thermostat', 'ThermoSmart', 'Ubi', 'WallyHome', 'Wattio GATE', 'Wattio POD', 'Wattio THERMIC', 'WeMo Air Purifier', 'WeMo Coffeemaker', 'WeMo Heater', 'WeMo Humidifier', 'WeMo Insight Switch', 'WeMo Light Switch', 'WeMo Lighting', 'WeMo Maker', 'WeMo Motion', 'WeMo Slow Cooker', 'WeMo Switch', 'WIFIPLUG', 'Wink: Aros', 'Wink: Egg Minder', 'Wink: Nimbus', 'Wink: Pivot Power Genius', 'Wink: Porkfolio', 'Wink: Shortcuts', 'Wink: Spotter', 'Android Device', 'Android Location', 'Android Phone Call', 'Android SMS', 'abode', 'Arlo', 'BloomSky', 'Camio', 'Home8', 'Homeboy', 'HomeControl Flex', 'iSecurity+', 'iSmartAlarm', 'Ivideon', 'Manything', 'Myfox HomeControl', 'Myfox Security', 'Nest Cam', 'Netatmo Welcome', 'Oco Camera', 'Piper', 'RemoteLync', 'Ring', 'Scout Alarm', 'Sighthound Video', 'SkyBell HD', 'Withings Home'])

data = []
dd_dict = functools.partial(collections.defaultdict, dict)
channels = collections.defaultdict(dd_dict)

with open('./coreresults.tsv', mode='r', encoding='UTF-8') as f:
    for line in f:
        line = line.strip()
        columns = line.split('\t')

        trigger_channel = columns[TRIGGER_CHANNEL_IDX]
        trigger = columns[TRIGGER_IDX]
        action_channel = columns[ACTION_CHANNEL_IDX]
        action = columns[ACTION_IDX]

        trigger_variable = '_'.join((trigger_channel, trigger)).replace(' ', '_')
        channels[trigger_channel]['triggers'][trigger] = {
                'variable': trigger_variable,
                'operator': '=',
                'value': 'true'
                }
        channels[trigger_channel]['variables'][trigger_variable] = {
                'type': '',
                'minValue': 0,
                'maxValue': 0,
                'value': ['on', 'off']
                }

        action_variable = '_'.join((action_channel, action)).replace(' ', '_')
        channels[action_channel]['actions'][action] = [ {
            'variable': action_variable,
            'value': '*'
            }]
        channels[action_channel]['variables'][action_variable] = {
                'type': '',
                'minValue': 0,
                'maxValue': 0,
                'value': ['on', 'off']
                }


for channel in channels:
    with open('channels/' + channel + '.json.todo', mode='w', encoding='UTF-8') as f:
        f.write(json.dumps(channels[channel], sort_keys=True, indent=4))
