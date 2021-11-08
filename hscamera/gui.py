import time

from PyQt5.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QSlider, QDoubleSpinBox, QComboBox
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtCore import QTimer
import qtwidgets
import sys
import numpy as np
from new_camera import Camera


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.cam = Camera(window=False)
        self.cam.start()
        time.sleep(1)
        self.setup_gui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)
        self.timer.start(30)

    def update_image(self):
        im = self.cam._get_img()
        self.image_viewer.setImage(im)

    def update_slider_ranges(self, val):
        max_framerate = self.cam.get_max_framerate()
        print('max framerate = ', max_framerate)

    def setup_gui(self):
        self.setWindowTitle('High Speed Camera GUI')
        self.image_viewer = qtwidgets.QImageViewer(self)
        im = self.cam._get_img()
        self.image_viewer.setImage(im)

        layout = QHBoxLayout()
        layout.addWidget(self.image_viewer)

        tool_layout = QVBoxLayout()
        layout.addLayout(tool_layout, 0.3)

        self.exposure_slider = qtwidgets.QCustomSlider(self, 'Exposure', 1, self.cam.get_max_exposure(), 1, value_=self.cam.settings['exposure'], label=True)
        self.exposure_slider.valueChanged.connect(self.cam.set_exposure)
        tool_layout.addWidget(self.exposure_slider)

        self.gain_slider = qtwidgets.QCustomSlider(self, 'Gain', 1, 4, 1, value_=self.cam.settings['gain'], label=True)
        self.gain_slider.valueChanged.connect(self.cam.set_gain)
        tool_layout.addWidget(self.gain_slider)

        self.fpn_correct_slider = qtwidgets.QCustomSlider(self, 'FPN correction', 0, 1, 1, value_=self.cam.settings['fpn_correction'], label=True)
        self.fpn_correct_slider.valueChanged.connect(self.cam.set_fpn_correction)
        tool_layout.addWidget(self.fpn_correct_slider)

        self.blacklevel_slider = qtwidgets.QCustomSlider(self, 'Blacklevel', 0, 255, 1, value_=self.cam.settings['blacklevel'], label=True)
        self.blacklevel_slider.valueChanged.connect(self.cam.set_blacklevel)
        tool_layout.addWidget(self.blacklevel_slider)

        self.height_slider = qtwidgets.QCustomSlider(self, 'Height', 0, 1024, 2, value_=self.cam.settings['height'], label=True)
        self.height_slider.valueChanged.connect(self.cam.set_height)
        self.height_slider.valueChanged.connect(self.update_slider_ranges)
        tool_layout.addWidget(self.height_slider)

        self.width_slider = qtwidgets.QCustomSlider(self, 'Width', 0, 1024, 16, value_=self.cam.settings['width'], label=True)
        self.width_slider.valueChanged.connect(self.cam.set_width)
        self.width_slider.valueChanged.connect(self.update_slider_ranges)
        tool_layout.addWidget(self.width_slider)

        self.framerate_slider = qtwidgets.QCustomSlider(self, 'Framerate', 10, self.cam.get_max_framerate(), 1, value_=self.cam.settings['framerate'], label=True)
        self.framerate_slider.valueChanged.connect(self.cam.set_framerate)
        tool_layout.addWidget(self.framerate_slider)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.resize(1024, 720)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec_()