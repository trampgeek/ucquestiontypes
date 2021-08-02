"""Define support functions for testing of matplotlib questions.
   The main function is print_plot_info, which displays suitably formatted
   data about the current matplotlib plot.

   This module works only if imported *after* a call to matplotlibg.use("Agg") has
   been done.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors as colors
from scipy import interpolate

MAX_LABEL_LENGTH = 60  # Use multiline display if the tick label string length exceeds this

def my_interpolate(data, xs):
    """Return the spline interpolated list of (x, y) values at abscissa xs, given
       a list of (x, y) pairs
    """
    def linear(x, x0, y0, x1, y1):
        return y0 + (x - x0)/(x1 - x0) * (y1 - y0)
    
    if len(data[:,0]) == 2:
        x0, y0 = data[0][0], data[0][1]
        x1, y1 = data[-1][0], data[-1][1]
        return [(x, linear(x, x0, y0, x1, y1)) for x in xs]
    else: # cubic
        tck = interpolate.splrep(data[:,0], data[:,1], s=0) # Cubic spline interpolator
        return zip(xs, interpolate.splev(xs, tck))  # Evaluate at required x values


def fmt_float_pair(p):
    """A formatted point or other pair of floating-point numbers"""
    return f"({p[0]:.2f}, {p[1]:.2f})"


def tick_fmt(tick):
    """Format a tick label, which may be either a string or a float. If it's
       a float, try to format it as an int, otherwise format it to 2 decimal
       places.
    """
    if isinstance(tick, str):
        return tick
    elif float(int(tick)) == tick:
        return str(int(tick))
    else:
        return f"{tick:.2f}"
    
    
def normalise_colour(colour):
    """Given a matplotlib colour, convert to a standarised format"""
    rgb = colors.to_rgb(colour)
    return f"RGB({rgb[0]:0.2f}, {rgb[1]:0.2f}, {rgb[2]:0.2f})"


def print_lines(subplot, x_samples, show_colour, has_legend):
    """Print all lines in the plot showing y values interplolated at the given x sample points,
       if not None. Otherwise print just the first 5 and last 5 points. Also
       show line colours if show_colour is True.
    """
    lines = subplot.get_lines()
    if len(lines) == 0:
        print("No plotted lines found")
        return
    multilines = len(lines) > 1
    if multilines:
        print(f"{len(lines)} separate plots found")
    for i, line in enumerate(lines, 1):
        if multilines:
            print(f"Line {i}:")
        if show_colour:
            print("Color:", normalise_colour(line.get_color()))
        print("Marker:", line.get_marker())
        print("Line style:", line.get_linestyle())
        label = line.get_label()
        if has_legend and label:
            print("Label:", label)
        data = line.get_xydata()
        if x_samples is not None:
            print(f"First point: {fmt_float_pair(data[0])}")
            print(f"Last point: {fmt_float_pair(data[-1])}")
            print(f"Interpolating line at selected x values:")
            interpolated = my_interpolate(data, x_samples)
            for p in interpolated:
                print(fmt_float_pair(p))
        else:
            print(f"Num points: {len(data)}")
            n = min(len(data), 5)
            points = '\n    '.join(fmt_float_pair(p) for p in data[:n])
            print(f"First {n} points:\n    {points}")
            last_n = min(len(data) - n, 5)
            if last_n:
                points = '\n    '.join(fmt_float_pair(p) for p in data[-last_n:])
                print(f"Last {last_n} points:\n    {points}")
        if multilines:
            print()


def in_range(labels, limits):
    """Return the list of axis labels, filtered to include only those within
       the given limits (min, max). If any of the axis labels are non-numeric
       the list is returned unchanged.
    """
    try:
        clipped_labels = []
        for s in labels:
            s_orig = s
            if isinstance(s, str):
                s = s.replace('−', '-')
            if limits[0] <= float(s) <= limits[1]:
                clipped_labels.append(s_orig)
        return clipped_labels
    except ValueError:
        return labels


def print_bars(subplot, show_colour):
    """Print a list of all bars"""
    print("Bars:")
    bars = subplot.patches
    if bars and show_colour:
        print(f"First bar colour: {normalise_colour(bars[0].get_facecolor())}")
    for i, bar in enumerate(subplot.patches):
        print(f"Bar{i}: x = {int(bar.get_xy()[0] + bar.get_width() / 2)} height = {bar.get_height():.2f}")
        
        
def tick_label_text(labels):
    """Return a string suitable for displaying tick labels"""
    label_text = ', '.join(labels)
    if len(label_text) > MAX_LABEL_LENGTH:
        label_text = '\n'.join(labels)
    return label_text   


def print_plot_info(data_type, x_samples=None,
                    show_xlim=False, show_ylim=False,
                    show_colour=False,
                    show_xticklabels=None,  # Default is True for bar chars, False otherwise
                    show_yticklabels=False
                    ):
    """Output key attributes of current plot, as defined by plt.gca().
       data_type must be one of 'points', 'lines' or 'bars', to print the
       appropriate type of data.
       x_samples, meaningful only if data_type = 'lines', is a list of x values
       at which the graph y values should be printed
    """
    try:
        axes = plt.gcf().get_axes()
        texts = plt.gcf().texts
        if len(axes) > 1:
            print(f"Figure has {len(axes)} subplots")
        if len(texts) != 0:
            print(f"Suptitle: {texts[0].get_text()}\n")
        for i, current_axes in enumerate(axes, 1):
            if len(axes) > 1:
                print(f"Subplot {i}\n---------")
            subplot = current_axes.axes
            has_legend = subplot.get_legend() is not None
            print("Plot title: '{}'".format(current_axes.title.get_text()))
            print("X-axis label: '{}'".format(subplot.get_xlabel()))
            print("Y-axis label: '{}'".format(subplot.get_ylabel()))
            xgridlines = subplot.get_xgridlines()
            ygridlines = subplot.get_ygridlines()
            gridx_on = len(xgridlines) > 0 and xgridlines[0].get_visible()
            gridy_on = len(ygridlines) > 0 and ygridlines[0].get_visible()
            print(f"(x, y) grid lines enabled: ({gridx_on}, {gridy_on})")
            xlim = subplot.get_xlim()
            ylim = subplot.get_ylim()
            if show_xlim:
                print(f"X-axis limits: {fmt_float_pair(xlim)}")
            if show_ylim:
                print(f"Y-axis limits: {fmt_float_pair(ylim)}")
            if data_type == 'points':
                print_lines(subplot, None, show_colour, has_legend)
            elif data_type == 'lines':
                print_lines(subplot, x_samples, show_colour, has_legend)
            elif data_type == 'bars':
                print_bars(subplot, show_colour)

            if show_xticklabels or (show_xticklabels is None and data_type == 'bars'):
                x_tick_labels = [label.get_text() for label in subplot.get_xticklabels()]
                if all(label.strip() == '' for label in x_tick_labels):
                    x_tick_labels = [tick_fmt(pos) for pos in subplot.get_xticks()]
                x_tick_labels = in_range(x_tick_labels, xlim)
                print('\nX-axis tick labels:')
                print(tick_label_text(x_tick_labels))
                
            if show_yticklabels:
                y_tick_labels = [label.get_text() for label in subplot.get_yticklabels()]
                if all(label.strip() == '' for label in y_tick_labels):
                    y_tick_labels = [tick_fmt(pos) for pos in subplot.get_yticks()]
                y_tick_labels = in_range(y_tick_labels, ylim)
                print("\nY-axis tick labels:")
                print(tick_label_text(y_tick_labels))
                
            if has_legend:
                print(f"Legend: True")
                
            if len(axes) > 1:
                print(40 * "=")
                print()
                

    except Exception as exception:
        print("Failed to get plot info:", str(exception))
