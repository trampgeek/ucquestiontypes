"""Dummy docstring for a function"""
import os
import matplotlib as _mpl
_mpl.use("Agg")
from __plottools import print_plot_info
import numpy as np
import matplotlib.pyplot as plt

class Plotter:
    def __init__(self, title, x_label, y_label, grid):
        self.axes = plt.axes()
        self.axes.set_title(title)
        self.axes.set_xlabel(x_label)
        self.axes.set_ylabel(y_label)
        if grid:
            self.axes.grid()

    def add_plot(self, xs, ys, marker, linestyle, label):
        self.axes.plot(xs, ys, marker=marker, linestyle=linestyle, 
                       label=label)
        self.last_xs = np.array(xs)
        self.last_ys = np.array(ys)

    def fit_last_line(self):
        self.a, self.b = np.polyfit(self.last_xs, self.last_ys, 1)
        return self.a, self.b

    def display(self):
        self.axes.legend()
        #plt.show()
