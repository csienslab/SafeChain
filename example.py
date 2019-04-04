import json
import random

from SafeChain.Controller import Controller
from SafeChain.Channel import Channel
from SafeChain.PrivacyPolicy import PrivacyPolicy
import SafeChain.Variable as Variable


def get_channel_definition(channel):
    with open(f'channels/{channel}.json') as f:
        definition = json.load(f)
    return definition

def set_rand_state(channel):
    possible_values_of_variables = channel.getPossibleValuesOfVariables()
    state = {variable_name: random.choice(tuple(possible_values))
              for variable_name, possible_values
              in possible_values_of_variables.items()}
    channel.setState(state)

def main():
    channels = ['Android Location', 'Philips Hue']

    # create channel database
    database = {channel: get_channel_definition(channel) for channel in channels}

    # initialize controller
    controller = Controller(database)

    # create channel objects
    location = Channel('Android Location', database['Android Location'],
                      'androidloc')
    location.setState({'location': 50, 'location_previous': 0})

    hue = Channel('Philips Hue', database['Philips Hue'], 'hue')
    set_rand_state(hue)

    controller.addChannel(location)
    controller.addChannel(hue)

    # create rule
    rule_name = 'RULE'
    trigger_channel = 'Android Location'
    trigger_name = 'You enter an area'
    action_channel = 'Philips Hue'
    action_name = 'Turn on lights'
    trigger_input = ('androidloc', 100)
    action_input = controller.getFeasibleInputsForAction(action_channel,
                                                         action_name)

    controller.addRule(rule_name, trigger_channel, trigger_name, trigger_input,
                       action_channel, action_name, action_input)

    # set policies
    controller.addVulnerableChannelVariable('hue', 'status')
    policy = PrivacyPolicy(set([('androidloc', 'location')]))

    # check
    filename, result, *time = controller.check(policy)
    print(result)

if __name__ == '__main__':
    main()
