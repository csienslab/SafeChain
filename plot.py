#!/usr/bin/env python3

import pickle
import operator
import statistics
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy
import math

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--filename', type=str, required=True, help='the file name of pickle file')
    parser.add_argument('--prefix', type=str, required=True, help='the prefix name of result files')
    args = parser.parse_args()

    with open(args.filename, 'rb') as f:
        data = pickle.load(f)

    original_times = data['original_times']
    optimized_times = data['optimized_times']
    args.min_number_of_rules = min(original_times.keys())
    args.max_number_of_rules = max(original_times.keys())
    args.step_size = (args.max_number_of_rules - args.min_number_of_rules) // (len(original_times.keys()) - 1)
    args.number_of_trials = len(original_times[args.min_number_of_rules])
    print(args)

    timegetter = operator.itemgetter(1, 2, 3, 4)
    # scatter plot
    plt.figure()
    x = tuple(number_of_rules for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size) for i in range(args.number_of_trials))
    y = tuple(sum(timegetter(original_times[number_of_rules][i])) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size) for i in range(args.number_of_trials))
    plt.scatter(x, y, color='r', marker='+', alpha=0.5)

    y = tuple(sum(timegetter(optimized_times[number_of_rules][i])) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size) for i in range(args.number_of_trials))
    plt.scatter(x, y, color='g', marker='x', alpha=0.5)

    plt.xlabel('Number of rules')
    plt.ylabel('Time (s)')
    plt.savefig('{}_scatter.pdf'.format(args.prefix))

    # average plot
    plt.figure()
    x = tuple(number_of_rules for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    y = tuple(statistics.mean(sum(timegetter(original_times[number_of_rules][i])) for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    plt.plot(x, y, 'r--')

    y = tuple(statistics.mean(sum(timegetter(optimized_times[number_of_rules][i])) for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    plt.plot(x, y, 'g:')

    plt.xlabel('Number of rules')
    plt.ylabel('Average time of checking (s)')
    plt.savefig('{}_average.pdf'.format(args.prefix))

    # bar plot
    plt.figure()
    fig, ax = plt.subplots()

    width = 0.35
    N = len(range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    ind = numpy.arange(N)
    means = tuple(statistics.mean(sum(timegetter(original_times[number_of_rules][i])) for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects1 = ax.bar(ind, means, width, color='gray', edgecolor='black', log=True)

    means = tuple(statistics.mean(sum(timegetter(optimized_times[number_of_rules][i])) for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects2 = ax.bar(ind + width, means, width, color='white', edgecolor='black', log=True)

    ax.set_ylabel('Time (s)')
    ax.set_xlabel('Number of rules')
    ax.set_xticks(ind + width / 2)
    ax.set_xticklabels(tuple(number_of_rules for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size)))
    ax.legend((rects1[0], rects2[0]), ('Without optimization', 'With optimization'), loc='upper left', ncol=1, frameon=False)
    ax.set_ylim([0.05, 5000])

    plt.savefig('{}_bar.pdf'.format(args.prefix), bbox_inches='tight', pad_inches=0.0)

    # optimized bar chart
    plt.figure()

    x = tuple(number_of_rules for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    y = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[0] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    line_grouping, = plt.plot(x, y, 'g--')

    y = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[1] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    line_pruning, = plt.plot(x, y, 'r-.')

    y = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[2] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    line_parsing, = plt.plot(x, y, 'b:')

    y = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[3] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    line_checking, = plt.plot(x, y)

    plt.legend([line_grouping, line_pruning, line_parsing, line_checking], ['Grouping', 'Pruning', 'Parsing', 'Checking'])
    plt.xlabel('Number of rules')
    plt.ylabel('Time (s)')
    plt.savefig('{}_optimize.pdf'.format(args.prefix))

    # optimized stack bar chart
    plt.figure()
    width = 0.35
    N = len(range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    ind = numpy.arange(N)

    grouping_means = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[0] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects1 = plt.bar(ind, grouping_means, width)

    bottom = tuple(map(sum, zip(grouping_means)))
    pruning_means = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[1] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects2 = plt.bar(ind, pruning_means, width, color='lawngreen', bottom=bottom)

    bottom = tuple(map(sum, zip(grouping_means, pruning_means)))
    parsing_means = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[2] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects3 = plt.bar(ind, parsing_means, width, color='magenta', bottom=bottom)

    bottom = tuple(map(sum, zip(grouping_means, pruning_means, parsing_means)))
    checking_means = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[3] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects4 = plt.bar(ind, checking_means, width, color='gray', bottom=bottom)

    plt.ylabel('Time (s)')
    plt.xlabel('Number of rules')
    plt.xticks(ind, range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    plt.legend((rects1[0], rects2[0], rects3[0], rects4[0]), ('Grouping', 'Pruning', 'Parsing', 'Checking'), bbox_to_anchor=(0, 1.02, 1, 0.2), loc='lower left', mode='expand', ncol=4, frameon=False)
    plt.savefig('{}_optimize_stack.pdf'.format(args.prefix))

    # optimized stack bar chart
    # https://stackoverflow.com/questions/17976103/matplotlib-broken-axis-example-uneven-subplot-size
    ylim = [0.07, 0.13]
    ylim2 = [0, 0.01]
    ylimratio = (ylim[1]-ylim[0])/(ylim2[1]-ylim2[0]+ylim[1]-ylim[0])
    ylim2ratio = (ylim2[1]-ylim2[0])/(ylim2[1]-ylim2[0]+ylim[1]-ylim[0])
    gs = gridspec.GridSpec(2, 1, height_ratios=[ylimratio, ylim2ratio])

    fig = plt.figure()
    ax = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1])

    width = 0.35
    N = len(range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    ind = numpy.arange(N)

    grouping_means = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[0] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects1 = ax.bar(ind, grouping_means, width, color='white', edgecolor='black')
    ax2.bar(ind, grouping_means, width, color='white', edgecolor='black')

    bottom = tuple(map(sum, zip(grouping_means)))
    pruning_means = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[1] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects2 = ax.bar(ind, pruning_means, width, bottom=bottom, color='white', edgecolor='black', hatch='xxx')
    ax2.bar(ind, pruning_means, width, bottom=bottom, color='white', edgecolor='black', hatch='xxx')

    bottom = tuple(map(sum, zip(grouping_means, pruning_means)))
    parsing_means = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[2] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects3 = ax.bar(ind, parsing_means, width, bottom=bottom, color='gray', edgecolor='black')
    ax2.bar(ind, parsing_means, width, bottom=bottom, color='gray', edgecolor='black')

    bottom = tuple(map(sum, zip(grouping_means, pruning_means, parsing_means)))
    checking_means = tuple(statistics.mean(timegetter(optimized_times[number_of_rules][i])[3] for i in range(args.number_of_trials)) for number_of_rules in range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size))
    rects4 = ax.bar(ind, checking_means, width, bottom=bottom, color='white', edgecolor='black', hatch='...')
    ax2.bar(ind, checking_means, width, bottom=bottom, color='white', edgecolor='black', hatch='...')

    ax.set_ylim(ylim)
    ax2.set_ylim(ylim2)
    plt.subplots_adjust(hspace=0.1)

    ax.spines['bottom'].set_visible(False)
    ax.xaxis.tick_top()
    ax.tick_params(axis='x', which='both', bottom='off', top='off', labeltop='off')
    ax2.spines['top'].set_visible(False)
    ax2.xaxis.tick_bottom()

    ax.set_ylabel('Time (s)')
    ax.yaxis.set_label_coords(0.05, 0.5, transform=fig.transFigure)
    ax.legend((rects1[0], rects2[0], rects3[0], rects4[0]), ('Grouping', 'Pruning', 'Parsing', 'Checking'), loc='upper left', ncol=2, frameon=False)
    ax2.set_xlabel('Number of rules')
    ax2.set_xticks(ind, minor=False)
    ax2.set_xticklabels(range(args.min_number_of_rules, args.max_number_of_rules + 1, args.step_size), minor=False, fontdict=None)

    kwargs = dict(color='k', clip_on=False)
    xlim = ax.get_xlim()
    dx = .01*(xlim[1]-xlim[0])
    dy = .005*(ylim[1]-ylim[0])/ylimratio
    ax.plot((xlim[0]-dx,xlim[0]+dx), (ylim[0]-dy,ylim[0]+dy), **kwargs)
    ax.plot((xlim[1]-dx,xlim[1]+dx), (ylim[0]-dy,ylim[0]+dy), **kwargs)
    dy = .005*(ylim2[1]-ylim2[0])/ylim2ratio
    ax2.plot((xlim[0]-dx,xlim[0]+dx), (ylim2[1]-dy,ylim2[1]+dy), **kwargs)
    ax2.plot((xlim[1]-dx,xlim[1]+dx), (ylim2[1]-dy,ylim2[1]+dy), **kwargs)
    ax.set_xlim(xlim)
    ax2.set_xlim(xlim)

    plt.savefig('{}_optimize_stack_skip.pdf'.format(args.prefix), bbox_inches='tight', pad_inches=0.0)
