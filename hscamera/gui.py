import time

from PyQt5.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QSlider, QDoubleSpinBox, QComboBox, QProgressBar, QStatusBar
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

        app.aboutToQuit.connect(self.quit)

    def update_image(self):
        im = self.cam.get_current_img()
        self.image_viewer.setImage(im)

    def width_changed(self, val):
        self.cam.set_width(val)
        self.update_max_framerate()
        self.update_x_max(val)

    def update_x_max(self, val):
        old_val = self.x_slider.value()
        self.x_slider.changeSettings(0, 1024-val, 1, old_val)
        self.x_slider.setEnabled(val != 1024)

    def update_y_max(self, val):
        old_val = self.y_slider.value()
        self.y_slider.changeSettings(0, 1024-val, 1, old_val)
        self.y_slider.setEnabled(val != 1024)

    def height_changed(self, val):
        self.cam.set_height(val)
        self.update_max_framerate()
        self.update_y_max(val)

    def x_changed(self, val):
        self.cam.set_x(val)

    def y_changed(self, val):
        self.cam.set_y(val)

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
        self.images = images

        self.lock_options()

        self.progress_bar.show()
        self.progress_bar.setRange(0, seconds)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage('Recording...')
        print("Record {} images".format(images))
        self.cam.start(images)
        self.thread = QThread(self)

        self.worker = RecordWorker()
        self.worker.seconds = seconds
        self.worker.filename = None
        self.worker.cam = self.cam

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)

        self.worker.recorded.connect(self.finish_recording)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.finish_saving)
        self.thread.start()

    def lock_options(self):
        self.exposure_slider.setEnabled(False)
        self.gain_slider.setEnabled(False)
        self.fpn_correct_slider.setEnabled(False)
        self.blacklevel_slider.setEnabled(False)
        self.width_slider.setEnabled(False)
        self.height_slider.setEnabled(False)
        self.framerate_slider.setEnabled(False)
        self.seconds_slider.setEnabled(False)
        self.record_button.setEnabled(False)

    def unlock_options(self):
        self.exposure_slider.setEnabled(True)
        self.gain_slider.setEnabled(True)
        self.fpn_correct_slider.setEnabled(True)
        self.blacklevel_slider.setEnabled(True)
        self.width_slider.setEnabled(True)
        self.height_slider.setEnabled(True)
        self.framerate_slider.setEnabled(True)
        self.seconds_slider.setEnabled(True)
        self.record_button.setEnabled(True)

    def finish_recording(self):
        self.cam.stop()
        self.status_bar.showMessage('Saving Video ...')
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(self.images)

    def finish_saving(self):
        self.progress_bar.hide()
        self.unlock_options()
        self.status_bar.showMessage('Ready')


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

        self.status_bar = QStatusBar()
        self.status_bar.showMessage('Ready')
        self.setStatusBar(self.status_bar)

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

        self.x_slider = qtwidgets.QCustomSlider(self, 'x start', 0, 0, 1, value_=self.cam.settings['x'], label=True)
        self.x_slider.valueChanged.connect(self.x_changed)
        tool_layout.addWidget(self.x_slider)
        if self.cam.settings['width'] == 1024:
            self.x_slider.setEnabled(False)

        self.y_slider = qtwidgets.QCustomSlider(self, 'y start', 0, 0, 1, value_=self.cam.settings['y'], label=True)
        self.y_slider.valueChanged.connect(self.y_changed)
        tool_layout.addWidget(self.y_slider)
        if self.cam.settings['height'] == 1024:
            self.y_slider.setEnabled(False)


        self.framerate_slider = qtwidgets.QCustomSlider(self, 'Framerate', 20, self.cam.get_max_framerate(), 1, value_=self.cam.settings['framerate'], label=True)
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

    def quit(self):
        print("Cleaning up before quitting")
        self.cam.stop()
        self.cam.clear_buffer()


class RecordWorker(QObject):
    recorded = pyqtSignal()
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def run(self):
        for i in range(self.seconds):
            time.sleep(1)
            self.progress.emit(i+1)
        self.recorded.emit()
        self.cam.save_vid(self.filename, self.update_progress)
        self.finished.emit()

    def update_progress(self, i):
        self.progress.emit(i)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec_()