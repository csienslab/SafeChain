#!/usr/bin/env python3

import copy
import re
import random
import collections

import variable as myvariable
import action as myaction
import trigger as mytrigger
import custom as mycustom

class Channel:
    def __init__(self, name, content):
        self.name = name
        self.variables = dict()
        self.triggers = dict()
        self.actions = dict()
        self.customs = dict()

        # make a copy for modification
        content = copy.copy(content)

        # update if empty
        if 'actions' not in content:
            content['actions'] = dict()

        if 'triggers' not in content:
            content['triggers'] = dict()

        if 'customs' not in content:
            content['customs'] = dict()

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

        # use custom constructor and check if there are errors in custom
        for variable_name, custom_content in content['customs'].items():
            custom = mycustom.Custom(self.name, variable_name, custom_content, self.variables)
            self.customs[variable_name] = custom

    def hasCustomEvents(self):
        return len(self.customs) != 0

    def getModuleName(self, device_name):
        channel_name = re.sub('[^A-Za-z0-9_]+', '', self.name).upper()
        return '{}_{}'.format(channel_name, device_name)

    def getRandomInputForTrigger(self, trigger_name, devices):
        trigger = self.triggers[trigger_name]

        inputs = list()
        for requirement in trigger.input_requirements:
            if requirement['type'] == 'device':
                values = devices
            elif requirement['type'] == 'value':
                variable_name = requirement['variable']
                variable = self.variables[variable_name]
                values = variable.getPossibleValues()
            elif requirement['type'] == 'set':
                values = requirement['setValue']

            value = random.choice(values)
            inputs.append(value)

        return inputs

    def getRandomInputForAction(self, action_name, devices):
        action = self.actions[action_name]

        inputs = list()
        for requirement in action.input_requirements:
            if requirement['type'] == 'device':
                values = devices
            elif requirement['type'] == 'value':
                variable_name = requirement['variable']
                variable = self.variables[variable_name]
                values = variable.getPossibleValues()
            elif requirement['type'] == 'set':
                values = requirement['setValue']

            value = random.choice(values)
            inputs.append(value)

        return inputs

    def getAssociatedRules(self, device_name, rules):
        associated_rules = list()
        for rule_name, rule in rules.items():
            if device_name in rule.action.getRequiredDevices(rule.action_inputs):
                associated_rules.append(rule)

        return associated_rules

    def getAssociatedVariableOperatorAndValue(self):
        results = list()
        for variable_name, custom in self.customs.items():
            result = custom.getAssociatedVariableOperatorAndValue()
            results += result

        for variable_name, variable in self.variables.items():
            if not isinstance(variable, myvariable.TimerVariable):
                continue

            results.append((variable_name, '=', None))

        return results

    def toNuSMVformat(self, database, device_name, device_state, rules, all_devices_name, grouping, all_variable_constraints):
        # associated rules and group by variable
        variable_rules = collections.defaultdict(list)
        associated_rules = self.getAssociatedRules(device_name, rules)
        for rule in associated_rules:
            for variable in rule.action.getDeviceAssociatedVariables(rule.action_inputs, device_name):
                variable_rules[variable].append(rule)

        # name
        name = self.getModuleName(device_name)

        # Module
        string  = 'MODULE {0}({1})\n'.format(name, ', '.join(all_devices_name))

        # define variables
        string += '  VAR\n'
        for variable_name in sorted(self.variables.keys()):
            variable = self.variables[variable_name]
            if grouping:
                values = variable.getPossibleValuesInNuSMVwithConstraints(all_variable_constraints[(device_name, variable_name)])
            else:
                values = variable.getPossibleValuesInNuSMV()

            string += '    {0}: {1};\n'.format(variable_name, values)
            if variable.previous:
                string += '    {0}: {1};\n'.format(variable_name + '_previous', values)
        string += '\n'

        # initial conditions
        string += '  ASSIGN\n'
        for variable_name in sorted(self.variables.keys()):
            variable = self.variables[variable_name]
            value = device_state[variable_name]
            if grouping:
                value = variable.getEquivalentAssignmentWithConstraints(all_variable_constraints[(device_name, variable_name)], value)

            string += '    -- init({0}) := {1};\n'.format(variable_name, device_state[variable_name])
            string += '    init({0}) := {1};\n'.format(variable_name, value)
            if variable.previous:
                string += '    init({0}) := {1};\n'.format(variable_name + '_previous', value)
        string += '\n'

        # rules and customs
        for variable_name in sorted(self.variables.keys()):
            variable = self.variables[variable_name]
            trigger_and_values = list()
            comments = list()

            if variable_name in variable_rules:
                for rule in variable_rules[variable_name]:
                    trigger_channel_name = rule.trigger.channel_name
                    trigger_variables = database[trigger_channel_name].variables

                    trigger = rule.trigger.toBooleanString(rule.trigger_inputs)
                    value = rule.action.getDeviceVariableAssociatedValues(rule.action_inputs, device_name, variable_name, self.variables)
                    comments.append((trigger, value))

                    if grouping:
                        trigger = rule.trigger.toEquivalentBooleanString(rule.trigger_inputs, trigger_variables, all_variable_constraints)
                        value = variable.getEquivalentAssignmentWithConstraints(all_variable_constraints[(device_name, variable_name)], value)

                    trigger_and_values.append((trigger, value))


            if variable_name in self.customs:
                custom = self.customs[variable_name]
                for trigger, value in custom.getTriggersAndValues(self.variables, device_name, all_variable_constraints):
                    comments.append((trigger, value))
                    trigger_and_values.append((trigger, value))

            if isinstance(variable, myvariable.TimerVariable):
                trigger = '{0} > 0'.format(variable_name)
                value = '{0} - 1'.format(variable_name)
                comments.append((trigger, value))
                trigger_and_values.append((trigger, value))

                trigger = '{0} = 0'.format(variable_name)
                value = variable.max_value if variable.repeat else -1
                comments.append((trigger, value))
                trigger_and_values.append((trigger, value))

            if hasattr(variable, 'reset_value') and variable.reset_value != None:
                comments.append(('TRUE', variable.reset_value))
                trigger_and_values.append(('TRUE', variable.reset_value))

            if variable.previous:
                string += '    next({0}) := {1};\n'.format(variable_name + '_previous', variable_name)

            if len(trigger_and_values) == 0:
                continue

            if len(trigger_and_values) == 1:
                trigger, value = trigger_and_values[0]
                if trigger == 'TRUE':
                    string += '    -- next({0}) := {1};\n'.format(comments[0][0], comments[0][1])
                    string += '    next({0}) := {1};\n'.format(variable_name, value)
                else:
                    string += '    -- next({0}) := {1} ? {2}: {0};\n'.format(variable_name, comments[0][0], comments[0][1])
                    string += '    next({0}) := {1} ? {2}: {0};\n'.format(variable_name, trigger, value)

            elif len(trigger_and_values) == 2 and trigger_and_values[1][0] == 'TRUE':
                trigger, value = trigger_and_values[0]
                _, value2 = trigger_and_values[1]
                string += '    -- next({0}) := {1} ? {2}: {3};\n'.format(variable_name, comments[0][0], comments[0][1], comments[1][1])
                string += '    next({0}) := {1} ? {2}: {3};\n'.format(variable_name, trigger, value, value2)

            else:
                string += '    next({0}) :=\n'.format(variable_name)
                string += '      case\n'
                for trigger_and_value, comment in zip(trigger_and_values, comments):
                    trigger, value = trigger_and_value
                    string += '        -- {0}: {1};\n'.format(comment[0], comment[1])
                    string += '        {0}: {1};\n\n'.format(trigger, value)
                if trigger_and_values[-1][0] != 'TRUE':
                    string += '        TRUE: {0};\n'.format(variable_name)
                string += '      esac;\n'

            string += '\n'

        return string


