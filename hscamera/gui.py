import time

from PyQt5.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QSlider, QDoubleSpinBox, QComboBox, QProgressBar
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtCore import QTimer, QThread, QObject
import qtwidgets
import sys
import numpy as np
from new_camera import Camera



class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.cam = Camera(window=False)
        self.cam.start()
        self.setup_gui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)
        self.timer.start(30)

        self.seconds = 10

    def update_image(self):
        im = self.cam.get_current_img()
        self.image_viewer.setImage(im)

    def width_changed(self, val):
        self.cam.set_width(val)
        self.update_max_framerate()

    def height_changed(self, val):
        self.cam.set_height(val)
        self.update_max_framerate()

    def framerate_changed(self, val):
        self.cam.set_framerate(val)
        self.update_max_exposure()

    def update_max_exposure(self):
        max_exposure = self.cam.get_max_exposure()
        exposure = self.cam.settings['exposure']
        if exposure > max_exposure:
            exposure = max_exposure
            self.cam.set_exposure(exposure)
        self.exposure_slider.changeSettings(1, max_exposure, 1, exposure)

    def update_max_framerate(self):
        max_framerate = self.cam.get_max_framerate()
        framerate = self.cam.settings['framerate']
        if framerate > max_framerate:
            framerate = max_framerate
            self.cam.set_framerate(framerate)
        self.framerate_slider.changeSettings(10, max_framerate, 1, framerate)

    def record_button_pressed(self):
        seconds = self.seconds_slider.value()
        images = seconds * self.framerate_slider.value()
        self.progress_bar.show()
        self.progress_bar.setRange(0, seconds)
        self.progress_bar.setValue(0)
        print("Record {} images".format(images))
        self.cam.start(images)
        self.thread = QThread(self)
        self.worker = RecordWorker()
        self.worker.seconds = seconds
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.update_recording_time)
        self.worker.finished.connect(self.finish_recording)
        self.thread.start()

    def update_recording_time(self, i):
        self.progress_bar.setValue(i)
        # print("Elapsed time : {} s".format(i))

    def finish_recording(self):
        self.cam.stop()
        self.cam.save_vid()
        self.progress_bar.hide()
        print("Finished recording")


    def seconds_slider_changed(self, val):
        self.seconds = val

    def setup_gui(self):
        self.setWindowTitle('High Speed Camera GUI')
        self.image_viewer = qtwidgets.QImageViewer(self)
        im = self.cam.get_current_img()
        self.image_viewer.setImage(im)

        layout = QVBoxLayout()
        hlayout = QHBoxLayout()
        layout.addLayout(hlayout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        hlayout.addWidget(self.image_viewer)

        tool_layout = QVBoxLayout()
        hlayout.addLayout(tool_layout, 0.3)

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
        self.height_slider.valueChanged.connect(self.height_changed)
        tool_layout.addWidget(self.height_slider)

        self.width_slider = qtwidgets.QCustomSlider(self, 'Width', 0, 1024, 16, value_=self.cam.settings['width'], label=True)
        self.width_slider.valueChanged.connect(self.width_changed)
        tool_layout.addWidget(self.width_slider)

        self.framerate_slider = qtwidgets.QCustomSlider(self, 'Framerate', 10, self.cam.get_max_framerate(), 1, value_=self.cam.settings['framerate'], label=True)
        self.framerate_slider.valueChanged.connect(self.framerate_changed)
        tool_layout.addWidget(self.framerate_slider)

        self.seconds_slider = qtwidgets.QCustomSlider(self, 'Record Time (s)', 1, 1000, 1, value_=10, label=True)
        self.seconds_slider.valueChanged.connect(self.seconds_slider_changed)
        tool_layout.addWidget(self.seconds_slider)

        self.record_button = QPushButton('Record', self)
        self.record_button.released.connect(self.record_button_pressed)
        tool_layout.addWidget(self.record_button)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.resize(1024, 720)


class RecordWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def run(self):
        for i in range(self.seconds):
            time.sleep(1)
            self.progress.emit(i+1)
        self.finished.emit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec_()