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

    def gain_changed(self, value):
        print(value)

    def setup_gui(self):
        self.setWindowTitle('High Speed Camera GUI')
        self.image_viewer = qtwidgets.QImageViewer(self)
        im = self.cam._get_img()
        self.image_viewer.setImage(im)

        layout = QHBoxLayout()
        layout.addWidget(self.image_viewer)

        tool_layout = QVBoxLayout()
        layout.addLayout(tool_layout, 0.3)

        exposure_slider = qtwidgets.QCustomSlider(self, 'Exposure', 1, self.cam.get_max_exposure(), 1, value_=self.cam.settings['exposure'], label=True)
        exposure_slider.valueChanged.connect(self.cam.set_exposure)
        tool_layout.addWidget(exposure_slider)

        gain_slider = qtwidgets.QCustomSlider(self, 'Gain', 1, 4, 1, value_=self.cam.settings['gain'], label=True)
        gain_slider.valueChanged.connect(self.cam.set_gain)
        tool_layout.addWidget(gain_slider)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.resize(1024, 720)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec_()