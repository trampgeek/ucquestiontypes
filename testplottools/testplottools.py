"""Testbed for hacking with plottools"""
import matplotlib.pyplot as plt
import __plottools as tools

def plot_bar1():
    axes = plt.axes()
    axes.bar(['first', 'second', 'third'], [10, 25, 3])

def plot_bar2():
    axes = plt.axes()
    axes.bar([0, 1, 2], [10, 25, 3], tick_label=['first', 'second', 'third'])

def plot_bar3():
    axes = plt.axes()
    axes.bar([100, 200, 300], [10, 25, 3])

def plot_bar4():
    axes = plt.axes()
    axes.bar(['100', '200', '300'], [10, 25, 3])


def test_bar():
    #plot_bar1()
    #plot_bar2()
    #plot_bar3()
    plot_bar4()

    tools.print_plot_info('bars', show_xticks=True, show_xticklabels=True)

def test_plot():
    xs = range(0, 10)
    ys = [x**2 for x in xs]
    axes = plt.axes()
    axes.plot(xs, ys)
    axes.set_xticks(xs, [xs)
    #plt.show()

def main():
    #test_bar()
    test_plot()
    tools.print_plot_info('points', show_xticks=True, show_xticklabels=True)

main()