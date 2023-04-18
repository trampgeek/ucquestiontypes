import matplotlib as _mpl
_mpl.use("Agg")
from __plottools import print_plot_info
import matplotlib.pyplot as plt
axes = plt.axes()
axes.plot(range(10), range(10))
axes.set_title("blah", name='Arial', size=30, color='red')
axes.set_xlabel("Twaddle, size 20", size=20)
axes.set_ylabel("More twaddle no size set")
#plt.show()
print_plot_info('lines', show_titlefont=True, show_colour=True)