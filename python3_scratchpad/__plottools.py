"""Define support functions for testing of matplotlib questions.
   The main function is print_plot_info, which displays suitably formatted
   data about the current matplotlib plot.

   This module works only if imported *after* a call to matplotlibg.use("Agg") has
   been done.
"""
import traceback
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors as colors
from scipy import interpolate

DEFAULT_PARAMS = {
    'x_samples': None,  # A list of x-values at which y values should be interpolated.
    'bar_indices': None,  # A list of the 0-origin bar indices to report on. None for all bars.
    'show_xlim': False,  # True to display the x-axis limits
    'show_ylim': False,  # True to display the y-axis limits
    'show_colour': False,  # True to report line/marker colour
    'show_xticklabels': None,  # True to display x-tick labels (defaults True for bars, False otherwise)
    'show_yticklabels': False,  # True to display y-tick labels
    'show_xticks': False,  # True to display x-tick numeric values
    'show_yticks': False,  # True to display y-tick numeric values
    'show_titlefont': False, # True to display title fontname and size
    'show_barx': True,  # True to print the x-coordinates of all bars
    'show_linelabels': None,  # True to show line labels, default is True if there's a legend else False
    'sort_points': False,  # True to sort data by x then y.
    'first_num_points': 5,  # Number of points to print at the start of the point list.
    'last_num_points': 5,  # Number of points to print at the end of the point list.
    'float_precision': (1, 1),  # Num digits to display after decimal point for x and y values resp
    'max_label_length': 60,  # Use multiline display if tick label string length exceeds this
    'lines_to_print': None,  # If non-None, a list of indices of lines to print (0 is first line).
    'line_info_only': False,  # True to suppress all except the line/bar/points info
}


class PlotChecker:
    """Wrapper for all the internal methods used to print plot info."""

    def __init__(self, params_dict):
        """Initialise with a subset of the options listed above"""
        self.params = DEFAULT_PARAMS.copy()
        self.params.update(params_dict)

    @staticmethod
    def my_interpolate(data, xs):
        """Return the spline interpolated list of (x, y) values at abscissa xs, given
           a list of (x, y) pairs
        """

        def linear(x, xa, ya, xb, yb):
            return ya + (x - xa) / (xb - xa) * (yb - ya)

        if len(data[:, 0]) == 2:
            x0, y0 = data[0][0], data[0][1]
            x1, y1 = data[-1][0], data[-1][1]
            return [(x, linear(x, x0, y0, x1, y1)) for x in xs]
        else:  # cubic
            tck = interpolate.splrep(data[:, 0], data[:, 1], s=0)  # Cubic spline interpolator
            return zip(xs, interpolate.splev(xs, tck))  # Evaluate at required x values

    @staticmethod
    def fmt_float(value, digits_precision=2):
        """Return a formatted floating point number to the precision specified,
           replacing -0 with 0"""
        format_string = f'.{digits_precision}f'
        s = format(value, format_string)
        if s.startswith('-') and float(s) == 0.0:
            s = s[1:]  # Strip off the minus sign.
        return s
        
    def fmt_float_axis(self, value, axis):
        """Format a given value as a float with the appropriate number of
           digits of precision for the specified axis ('x' or 'y').
           Except - string values are returned as is.
        """
        if isinstance(value, str):
            return value
        else:
            precision = self.params['float_precision'][0 if axis == 'x' else 1]
            return self.fmt_float(value, precision)

    def fmt_float_pair(self, p, precision=None):
        """A formatted (x, y) point or other pair of floating-point numbers.
           By default, use float_precision_x and float_precision_y for the
           first and second numbers resp, else use precision if given.
        """
        if precision is None:
            x_precision = self.params['float_precision'][0]
            y_precision = self.params['float_precision'][1]
        else:
            x_precision = y_precision = precision
        return f"({self.fmt_float(p[0], x_precision)}, {self.fmt_float(p[1], y_precision)})"

    @staticmethod
    def normalise_colour(colour):
        """Given a matplotlib colour, convert to a standarised format"""
        rgb = colors.to_rgb(colour)
        return f"RGB({rgb[0]:0.2f}, {rgb[1]:0.2f}, {rgb[2]:0.2f})"

    def print_line(self, line, xsamples):
        """Print the info for the given line"""
        if self.params['show_colour']:
            print("Color:", self.normalise_colour(line.get_color()))
        marker = line.get_marker()
        if marker == '':
            marker = None
        print("Marker:", marker)
        print("Line style:", line.get_linestyle())
        label = line.get_label()
        if label and self.params['show_linelabels']:
            print("Label:", label)
        data = line.get_xydata()

        if self.params['sort_points']:
            data = np.array(sorted([[row[0], row[1]] for row in data]))
            print("Plotted data, after sorting ...")

        if xsamples is not None:
            print(f"First point: {self.fmt_float_pair(data[0])}")
            print(f"Last point: {self.fmt_float_pair(data[-1])}")
            print(f"Interpolating line at selected x values:")
            interpolated = self.my_interpolate(data, xsamples)
            for p in interpolated:
                print('   ', self.fmt_float_pair(p))
        else:
            print(f"Num points: {len(data)}")
            n = min(len(data), self.params['first_num_points'])
            if n:
                points = '\n    '.join(self.fmt_float_pair(p) for p in data[:n])
                if n < len(data):
                    print(f"First {n} points:\n    {points}")
                else:
                    print(f"    {points}")
            last_n = min(len(data) - n, self.params['last_num_points'])
            if last_n:
                points = '\n    '.join(self.fmt_float_pair(p) for p in data[-last_n:])
                print(f"Last {last_n} points:\n    {points}")

    def print_lines(self, subplot, xsamples):
        """Print all selected lines in the plot showing y values interplolated at the x sample points,
           if given. Otherwise, print just the first first_num_points and last last_num_points. Also
           show line colours if the show_colour parameter is True.
        """
        lines = subplot.get_lines()
        if len(lines) == 0:
            print("No plotted lines found")
            return
        line_indices = self.params['lines_to_print']
        if line_indices is None:
            wanted_lines = lines
        else:
            wanted_lines = []
            for i in line_indices:
                if i >= len(lines):
                    print(f"Can't display info for plot {i} - no such plot!")
                    return
                else:
                    wanted_lines.append(lines[i])

        multilines = len(wanted_lines) > 1
        if multilines:
            print(f"Displaying info for {len(wanted_lines)} lines")
        for i, line in enumerate(wanted_lines, 1):
            if multilines:
                print(f"Line {i}:")
            self.print_line(line, xsamples)
            if multilines:
                print()

    @staticmethod
    def in_range(labels, limits):
        """Return the list of axis labels, filtered to include only those within
           the given limits (min, max). If any of the axis labels are non-numeric
           the list is returned unchanged.
        """
        try:
            clipped_labels = []
            for s in labels:
                if isinstance(s, str):
                    s = s.replace('−', '-')
                if limits[0] <= float(s) <= limits[1]:
                    clipped_labels.append(s)
            return clipped_labels
        except ValueError:
            return labels

    def print_bars(self, subplot):
        """Print a list of all bars if the bar_indices param is None or a list of the
           bars with the given indices, otherwise.
        """
        print("Bars:")
        bars = subplot.patches
        if bars and self.params['show_colour']:
            print(f"First bar colour: {self.normalise_colour(bars[0].get_facecolor())}")
        bar_indices = self.params['bar_indices']
        if bar_indices is None:
            bar_indices = range(0, len(subplot.patches))
        for i in bar_indices:
            try:
                bar = subplot.patches[i]
                y = bar.get_height()
                if self.params['show_barx']:
                    x = bar.get_xy()[0] + bar.get_width() / 2
                    bar_spec = f"Bar{i}: x = {self.fmt_float_axis(x, 'x')}, height = {self.fmt_float_axis(y, 'y')}"
                else:
                    bar_spec = f"Bar{i}: height = {self.fmt_float_axis(y, 'y')}"
                print(bar_spec)
            except IndexError:
                print(f"Bar{i} not found. Number of bars = {len(subplot.patches)}")
                break

    def tick_label_text(self, labels):
        """Return a string suitable for displaying tick labels (multiline or
           single line depending on length.
        """
        label_text = ', '.join(labels)
        if len(label_text) > self.params['max_label_length']:
            label_text = '\n'.join(labels)
        return label_text
    
    def print_ticks_for_axis(self, axis, subplot, axis_limit):
        """Print tick and ticklabel info for the given axis ('x' or 'y') of
           the given subplot. axis_limit is either xlim or ylim.
        """
        axis = axis.lower()  # Just to be safe
        if axis == 'x':
            ticks = subplot.get_xticks()
            tick_labels_obj = subplot.get_xticklabels()
        else:
            assert axis == 'y'
            ticks = subplot.get_yticks()
            tick_labels_obj = subplot.get_yticklabels()
            
        tick_labels = [label.get_text() for label in tick_labels_obj]
            
        if all(float(int(tick)) == tick for tick in ticks):
            # If all ticks are integers, don't format as floats
            formatted_ticks = [str(int(tick)) for tick in ticks]
        else:
            formatted_ticks = [self.fmt_float_axis(pos, axis) for pos in ticks]
        
        if self.params[f'show_{axis}ticks']:
            print(f'{axis.upper()}-axis ticks at ', ', '.join(formatted_ticks))

        if self.params[f'show_{axis}ticklabels']:
            # A problem here is that in a call to bar(axis_labels, bar_heights) the call to get_xticklabels doesn't
            # return the actual labels, but rather their tick locations. I can't find a workaround for this.
            if all(label.strip() == '' for label in tick_labels):
                tick_labels = formatted_ticks
            tick_labels = self.in_range(tick_labels, axis_limit)
            print(f'{axis.upper()}-axis tick labels:')
            print(self.tick_label_text(tick_labels))        
        

    def print_ticks(self, subplot, xlim, ylim):
        """Print tick and ticklabel info for the given subplot."""
        self.print_ticks_for_axis('x', subplot, xlim)
        self.print_ticks_for_axis('y', subplot, ylim)

    def print_axis_info(self, subplot):
        """Print the axis info for the given subplot"""

        print("X-axis label: '{}'".format(subplot.get_xlabel()))
        print("Y-axis label: '{}'".format(subplot.get_ylabel()))
        xgridlines = subplot.get_xgridlines()
        ygridlines = subplot.get_ygridlines()
        gridx_on = len(xgridlines) > 0 and bool(xgridlines[0].get_visible())
        gridy_on = len(ygridlines) > 0 and bool(ygridlines[0].get_visible())
        print(f"(x, y) grid lines enabled: ({gridx_on}, {gridy_on})")
        xlim = subplot.get_xlim()
        ylim = subplot.get_ylim()
        if self.params['show_xlim']:
            print(f"X-axis limits: {self.fmt_float_pair(xlim, precision=self.params['float_precision'][0])}")
        if self.params['show_ylim']:
            print(f"Y-axis limits: {self.fmt_float_pair(ylim, precision=self.params['float_precision'][1])}")
        self.print_ticks(subplot, xlim, ylim)

        if subplot.get_legend() is not None:
            print(f"Legend: True")
        print()

    def print_subplot_info(self, data_type, subplot, title):
        """Print the info for a single given subplot.
           If the data_type is 'lines' an optional parameter x_samples
           can be used to specify x values at which the line should be sampled.
           If the data_type is lines, the x-tick labels are shown unless
           the show_xticklabels parameters is explicitly set to False.
           title is a Text object, not a string.
        """
        if not self.params['line_info_only']:
            if self.params['show_xticklabels'] is None and data_type == 'bars':
                self.params['show_xticklabels'] = True
            has_legend = subplot.get_legend() is not None
            if has_legend and self.params['show_linelabels'] is None:
                self.params['show_linelabels'] = True
            title_text = title.get_text()
            print("Plot title: '{}'".format(title_text))
            if self.params['show_titlefont']:
                if self.params['show_colour']:
                    colour = ' ' + self.normalise_colour(title.get_color())
                else:
                    colour = ''
                print(f"Title font: {title.get_fontsize()} pt {title.get_fontfamily()[0]}{colour}")
            self.print_axis_info(subplot)

        if data_type == 'points':
            self.print_lines(subplot, None)
        elif data_type == 'lines':
            self.print_lines(subplot, self.params['x_samples'])
        elif data_type == 'bars':
            self.print_bars(subplot)

    def print_info(self, data_type):
        """Print all the information for the current plot. data_type
           must be 'points', 'lines' or 'bars'.
        """
        try:
            axes = plt.gcf().get_axes()
            texts = plt.gcf().texts
            if not self.params['line_info_only']:
                if len(axes) > 1:
                    print(f"Figure has {len(axes)} subplots")
                if len(texts) != 0:
                    print(f"Suptitle: {texts[0].get_text()}\n")
            for i, current_axes in enumerate(axes, 1):
                if len(axes) > 1 and not self.params['line_info_only']:
                    print(f"Subplot {i}\n---------")
                subplot = current_axes.axes
                title = current_axes.title
                self.print_subplot_info(data_type, subplot, title)
                if len(axes) > 1 and not self.params['line_info_only']:
                    print(40 * "=")
                    print()

        except Exception as e:
            print("Failed to get plot info:", repr(e))
            traceback.print_exception(e)


def print_plot_info(data_type, **kwparams):
    """Output key attributes of current plot, as defined by plt.gca().
       data_type must be one of 'points', 'lines' or 'bars', to print the
       appropriate type of data.
       For values of possible keyword parameters see DEFAULT_PARAMS declaration
    """

    unknown_params = set(kwparams) - set(DEFAULT_PARAMS)
    if unknown_params:
        print(f"Unknown parameter(s) passed to print_plot_info: {', '.join(unknown_params)}")
        return

    checker = PlotChecker(kwparams)
    checker.print_info(data_type)
