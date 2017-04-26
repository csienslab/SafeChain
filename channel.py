#!/usr/bin/env python3

import copy

import variable as myvariable
import action as myaction
import trigger as mytrigger

class Channel:
    def __init__(self, name, content):
        self.name = name
        self.variables = dict()
        self.triggers = dict()
        self.actions = dict()

        # make a copy for modification
        content = copy.copy(content)

        # update if empty
        if 'actions' not in content:
            content['actions'] = dict()

        if 'triggers' not in content:
            content['triggers'] = dict()


        # use variable constructor and check if there are errors
        for variable_name, variable_content in content['variables'].items():
            if variable_content['type'] == 'boolean':
                constructor = myvariable.BooleanVariable
            elif variable_content['type'] == 'set':
                constructor = myvariable.SetVariable
            elif variable_content['type'] == 'range':
                constructor = myvariable.RangeVariable
            elif variable_content['type'] == 'timer':
                constructor = myvariable.TimerVariable
            else:
                raise ValueError('[{0}] variable {1} with unsupported type'.format(self.name, variable_name))

            variable = constructor(self.name, variable_name, variable_content)
            self.variables[variable_name] = variable

        # use trigger constructor and check if there are errors in trigger
        for trigger_name, trigger_content in content['triggers'].items():
            trigger = mytrigger.Trigger(self.name, trigger_name, trigger_content, self.variables)
            self.triggers[trigger_name] = trigger

        # use action constructor and check if there are errors in action
        for action_name, action_content in content['actions'].items():
            action = myaction.Action(self.name, action_name, action_content, self.variables)
            self.actions[action_name] = action

