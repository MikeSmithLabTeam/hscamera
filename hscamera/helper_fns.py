from PyQt5.QtWidgets import QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, \
    NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

def write_paramdict_file(params, filename):
    with open(filename, 'w') as f:
        print(params, file=f)

def read_paramdict_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
        return eval(content)

def save_filename(initialdir=None, filter="all (*.*)", parent=None):
    options = QFileDialog.Options()
    # options |= QFileDialog.DontUseNativeDialog
    filename, ok = QFileDialog.getSaveFileName(parent, "save File", ' ',
                                                            filter, options=options)
    return filename

def get_filename(initialdir=None,filter="all (*.*)", parent=None):
    options = QFileDialog.Options()
    # options |= QFileDialog.DontUseNativeDialog
    filename, ok = QFileDialog.getSaveFileName(parent, "open File", '',
                                                            filter, options=options)
    return filename