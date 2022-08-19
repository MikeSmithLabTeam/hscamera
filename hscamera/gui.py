import time
import logging

from PyQt5.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QSlider, QDoubleSpinBox, QComboBox, QProgressBar, QStatusBar, QToolBar, QToolButton, QAction, QFileDialog
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtCore import QTimer, QThread, QObject
from PyQt5.QtGui import QIcon
import qtwidgets
import sys
import numpy as np
from camera import Camera



class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.cam = Camera()
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
        logging.debug('Width slider changed to {}'.format(val))
        self.cam.set_width(val)
        self.update_max_framerate()
        self.update_x_max(val)
        self.update_max_seconds()

    def update_x_max(self, width):
        old_val = self.x_slider.value()
        val = 1024 - width
        logging.debug('x_slider max set to {}'.format(val))
        self.x_slider.changeSettings(0, val, 16, old_val)
        self.x_slider.setEnabled(width != 1024)

    def update_y_max(self, height):
        old_val = self.y_slider.value()
        val = 1024 - height
        logging.debug('y_slider max set to {}'.format(val))
        self.y_slider.changeSettings(0, val, 2, old_val)
        self.y_slider.setEnabled(height != 1024)

    def height_changed(self, val):
        logging.debug('Height slider changed to {}'.format(val))
        self.cam.set_height(val)
        self.update_max_framerate()
        self.update_y_max(val)
        self.update_max_seconds()

    def x_changed(self, val):
        logging.debug('x slider changed to {}'.format(val))
        self.cam.set_x(val)

    def y_changed(self, val):
        logging.debug('y slider changed to {}'.format(val))
        self.cam.set_y(val)

    def framerate_changed(self, val):
        logging.debug('framerate slider changed to {}'.format(val))
        self.cam.set_framerate(val)
        self.update_max_exposure()
        self.update_max_seconds()

    def exposure_changed(self, val):
        logging.debug('exposure slider changed to {}'.format(val))
        self.cam.set_exposure(val)
        self.update_max_dualslope(val)

    def update_max_dualslope(self, exposure):
        logging.debug('Max dualslope set to {}'.format(exposure))
        self.dualslope_slider.changeSettings(0, exposure, 1)

    def dualslope_changed(self, val):
        logging.debug('dualslope slider change to {}'.format(val))
        if val == 0:
            self.cam.set_dualslope_state(0)
            self.cam.set_dualslope_time(1)
        else:
            self.cam.set_dualslope_state(1)
            self.cam.set_dualslope_time(val)
        self.update_max_tripleslope(val)

    def update_max_tripleslope(self, dualslope):
        logging.debug('Tripleslope max set to {}'.format(dualslope))
        self.tripleslope_slider.changeSettings(0, dualslope, 1)

    def tripleslope_changed(self, val):
        logging.debug('tripleslope slider changed to {}'.format(val))
        if val == 0:
            self.cam.set_tripleslope_state(0)
            self.cam.set_tripleslope_time(1)
        else:
            self.cam.set_tripleslope_state(1)
            self.cam.set_tripleslope_time(val)

    def update_max_exposure(self):
        max_exposure = self.cam.get_max_exposure()
        exposure = self.cam.settings['exposure']
        if exposure > max_exposure:
            exposure = max_exposure
            self.cam.set_exposure(exposure)
        logging.debug('exposure slider maximum set to {}'.format(max_exposure))
        self.exposure_slider.changeSettings(1, max_exposure, 1, exposure)

    def update_max_framerate(self):
        max_framerate = self.cam.get_max_framerate()
        framerate = self.cam.settings['framerate']
        if framerate > max_framerate:
            framerate = max_framerate
            self.cam.set_framerate(framerate)
        logging.debug('framerate slider maximum set to {}'.format(max_framerate))
        self.framerate_slider.changeSettings(10, max_framerate, 1, framerate)

    def update_max_seconds(self):
        max_num_pics = self.cam.get_max_numpics()
        max_seconds = max_num_pics / self.cam.settings['framerate']
        logging.debug('seconds slider maximum set to {}'.format(max_seconds))
        self.seconds_slider.changeSettings(1, max_seconds, 1)

    def record_button_pressed(self):
        logging.debug('record button pressed')
        seconds = self.seconds_slider.value()
        images = seconds * self.framerate_slider.value()
        self.images = images

        self.lock_options()

        self.progress_bar.show()
        self.progress_bar.setRange(0, seconds)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage('Recording...')
        logging.info('Recording of {} images starting'.format(images))
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
        logging.debug('Sliders locking')
        self.exposure_slider.setEnabled(False)
        self.gain_slider.setEnabled(False)
        self.fpn_correct_slider.setEnabled(False)
        self.blacklevel_slider.setEnabled(False)
        self.width_slider.setEnabled(False)
        self.height_slider.setEnabled(False)
        self.x_slider.setEnabled(False)
        self.y_slider.setEnabled(False)
        self.framerate_slider.setEnabled(False)
        self.seconds_slider.setEnabled(False)
        self.record_button.setEnabled(False)

    def unlock_options(self):
        logging.debug('Sliders unlocking')
        self.exposure_slider.setEnabled(True)
        self.gain_slider.setEnabled(True)
        self.fpn_correct_slider.setEnabled(True)
        self.blacklevel_slider.setEnabled(True)
        self.width_slider.setEnabled(True)
        self.height_slider.setEnabled(True)
        if self.cam.settings['height'] != 1024:
            self.y_slider.setEnabled(True)
        if self.cam.settings['width'] != 1024:
            self.x_slider.setEnabled(True)
        self.framerate_slider.setEnabled(True)
        self.seconds_slider.setEnabled(True)
        self.record_button.setEnabled(True)

    def finish_recording(self):
        logging.info('Recording finished')
        self.cam.stop()
        self.status_bar.showMessage('Saving Video ...')
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(self.images)

    def finish_saving(self):
        logging.info('Saving finished')
        self.progress_bar.hide()
        self.unlock_options()
        self.status_bar.showMessage('Ready')


    def seconds_slider_changed(self, val):
        logging.info('Seconds slider set to {}'.format(val))
        self.seconds = val

    def load_settings(self):
        logging.debug('Load settings clicked')
        fname = QFileDialog.getOpenFileName(self, caption='Open settings file', filter='JSON files (*.json)')
        self.cam.load_new_settings(fname[0])

    def save_settings(self):
        logging.debug('Save settings clicked')
        fname = QFileDialog.getSaveFileName(self, caption='Save settings file', filter='JSON files (*.json)')
        self.cam.save_settings(fname[0]+'.json')
       
    def update_sliders(self):
        #only called when loading settings file
        self.height_slider.slider.setValue(self.cam.settings['height'])
        self.height_slider.value_label.setText(str(self.cam.settings['height']))
        self.width_slider.slider.setValue(self.cam.settings['width'])
        self.width_slider.value_label.setText(str(self.cam.settings['width']))
        self.gain_slider.slider.setValue(self.cam.settings['gain'])
        self.gain_slider.value_label.setText(str(self.cam.settings['gain']))
        self.fpn_correct_slider.slider.setValue(self.cam.settings['fpn_correction'])
        self.fpn_correct_slider.value_label.setText(str(self.cam.settings['fpn_correction']))
        self.framerate_slider.slider.setValue(self.cam.settings['framerate'])
        self.framerate_slider.value_label.setText(str(self.cam.settings['framerate']))
        self.exposure_slider.slider.setValue(self.cam.settings['exposure'])
        self.exposure_slider.value_label.setText(str(self.cam.settings['exposure']))
        self.blacklevel_slider.slider.setValue(self.cam.settings['blacklevel'])
        self.blacklevel_slider.value_label.setText(str(self.cam.settings['blacklevel']))
        self.x_slider.slider.setValue(self.cam.settings['x'])
        self.x_slider.value_label.setText(str(self.cam.settings['x']))
        self.y_slider.slider.setValue(self.cam.settings['y'])
        self.y_slider.value_label.setText(str(self.cam.settings['y']))

    def setup_gui(self):
        logging.debug('Starting gui setup')
        self.setWindowTitle('High Speed Camera GUI')

        self.toolbar = self.addToolBar('File')
        self.load_action = QAction(QIcon("/usr/share/icons/HighContrast/16x16/actions/document-open.png"), 'Open settings', self)
        self.load_action.triggered.connect(self.load_settings)
        self.toolbar.addAction(self.load_action)

        self.save_action = QAction(QIcon("/usr/share/icons/HighContrast/16x16/actions/document-save.png"), 'Save settings', self)
        self.save_action.triggered.connect(self.save_settings)
        self.toolbar.addAction(self.save_action)



        self.image_viewer = qtwidgets.QImageViewer(self)
        im = self.cam.get_current_img()
        self.image_viewer.setImage(im)

        layout = QVBoxLayout()
        # layout.addWidget(self.toolbar)

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
        self.exposure_slider.valueChanged.connect(self.exposure_changed)
        self.exposure_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.exposure_slider)

        self.gain_slider = qtwidgets.QCustomSlider(self, 'Gain', 1, 4, 1, value_=self.cam.settings['gain'], label=True)
        self.gain_slider.valueChanged.connect(self.cam.set_gain)
        self.gain_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.gain_slider)

        self.fpn_correct_slider = qtwidgets.QCustomSlider(self, 'FPN correction', 0, 1, 1, value_=self.cam.settings['fpn_correction'], label=True)
        self.fpn_correct_slider.valueChanged.connect(self.cam.set_fpn_correction)
        self.fpn_correct_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.fpn_correct_slider)

        self.blacklevel_slider = qtwidgets.QCustomSlider(self, 'Blacklevel', 0, 255, 1, value_=self.cam.settings['blacklevel'], label=True)
        self.blacklevel_slider.valueChanged.connect(self.cam.set_blacklevel)
        self.blacklevel_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.blacklevel_slider)

        dualslope_val = 0 if self.cam.settings['dualslope'] == 0 else self.cam.settings['dualslope_time']
        self.dualslope_slider = qtwidgets.QCustomSlider(self, 'Dualslope', 0, self.cam.settings['exposure'], 1, value_=dualslope_val, label=True)
        self.dualslope_slider.valueChanged.connect(self.dualslope_changed)
        self.dualslope_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.dualslope_slider)

        tripleslope_val = 0 if self.cam.settings['tripleslope'] == 0 else self.cam.settings['tripleslope_time']
        self.tripleslope_slider = qtwidgets.QCustomSlider(self, 'Tripleslope', 0, self.cam.settings['dualslope_time'], 1, value_=tripleslope_val, label=True)
        self.tripleslope_slider.valueChanged.connect(self.tripleslope_changed)
        self.tripleslope_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.tripleslope_slider)

        self.height_slider = qtwidgets.QCustomSlider(self, 'Height', 2, 1024, 2, value_=self.cam.settings['height'], label=True)
        self.height_slider.valueChanged.connect(self.height_changed)
        self.height_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.height_slider)

        self.width_slider = qtwidgets.QCustomSlider(self, 'Width', 16, 1024, 16, value_=self.cam.settings['width'], label=True)
        self.width_slider.valueChanged.connect(self.width_changed)
        self.width_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.width_slider)

        self.x_slider = qtwidgets.QCustomSlider(self, 'x start', 0, 0, 16, value_=self.cam.settings['x'], label=True)
        self.x_slider.valueChanged.connect(self.x_changed)
        self.x_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.x_slider)
        if self.cam.settings['width'] == 1024:
            self.x_slider.setEnabled(False)

        self.y_slider = qtwidgets.QCustomSlider(self, 'y start', 0, 0, 2, value_=self.cam.settings['y'], label=True)
        self.y_slider.valueChanged.connect(self.y_changed)
        self.y_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.y_slider)
        if self.cam.settings['height'] == 1024:
            self.y_slider.setEnabled(False)


        self.framerate_slider = qtwidgets.QCustomSlider(self, 'Framerate', 20, self.cam.get_max_framerate(), 1, value_=self.cam.settings['framerate'], label=True)
        self.framerate_slider.valueChanged.connect(self.framerate_changed)
        self.framerate_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.framerate_slider)

        self.seconds_slider = qtwidgets.QCustomSlider(self, 'Record Time (s)', 1, 30, 1, value_=10, label=True)
        self.seconds_slider.valueChanged.connect(self.seconds_slider_changed)
        self.seconds_slider.settings_button.setVisible(False)
        tool_layout.addWidget(self.seconds_slider)

        self.record_button = QPushButton('Record', self)
        self.record_button.released.connect(self.record_button_pressed)
        tool_layout.addWidget(self.record_button)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.resize(1024, 720)

        logging.debug('Gui setup finished')

    def quit(self):
        logging.info('Cleaning up before quitting')
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
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    app.exec_()
