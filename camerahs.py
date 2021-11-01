import sys
sys.path.append("/opt/SiliconSoftware/Runtime5.7.0/SDKWrapper/PythonWrapper/python36/bin")
sys.path.append("/opt/SiliconSoftware/Runtime5.7.0/lib64")
import SiSoPyInterface as SISO

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QApplication,
                             QSlider, QHBoxLayout, QPushButton)
import qimage2ndarray as qim


import os
import cv2
import numpy as np

from filehandling import save_filename
from labvision.video import WriteVideo
from labvision.images import display, gray_to_bgr
from microscope.cam_settings import CameraSettings
import time
from threading import Timer
from qimage2ndarray import array2qimage




class Camera:
    def __init__(self, cam_config_dir='/opt/ConfigFiles/', filename=None, ccf_file=None):
        print('Opening Camera')
        self.cam_config_dir = cam_config_dir
        self.fg = SISO.Fg_InitConfig(cam_config_dir + 'current.mcf', 0)
        self.camset = CameraSettings(self, cam_config_dir, ccf_file=ccf_file)
        if filename is None:
            filename = save_filename(initialdir='~/Videos/')
        self.filename_base = filename.split('.')[0]

    def initialise(self):
        #Sets up ringbuffer
        totalBufferSize = self.camset.cam_dict['frameformat'][2][2] * self.camset.cam_dict['frameformat'][2][3] * self.camset.cam_dict['numpicsbuffer'][2]
        self.memHandle = SISO.Fg_AllocMemEx(self.fg, totalBufferSize, self.camset.cam_dict['numpicsbuffer'][2])
        self.display = SISO.CreateDisplay(8, self.camset.cam_dict['frameformat'][2][2],
                                          self.camset.cam_dict['frameformat'][2][3])
        SISO.SetBufferWidth(self.display, self.camset.cam_dict['frameformat'][2][2],
                            self.camset.cam_dict['frameformat'][2][3])

    def preview(self, mod_settings=True):
        self.grab()
        while True:
            if cv2.waitKey(0) & 0xFF == ord('q'):
                break
        print('out')
        self.trigger(numpics=0)
        self.close_display()

    def grab(self):
        #begins collecting imgs into ring buffer
        self.numpics = SISO.GRAB_INFINITE

        err = SISO.Fg_AcquireEx(self.fg, 0, self.numpics, SISO.ACQ_STANDARD, self.memHandle)

        if (err != 0):
            print('Fg_AcquireEx() failed:', SISO.Fg_getLastErrorDescription(self.fg))
            self.resource_cleanup()

        self.display_timer = DisplayTimer(0.03, self.display_img)
        self.display_timer.start()

    def trigger(self,numpics=None):
        self.numpics = numpics
        if numpics is None:
            picsaftertrigger = self.camset.cam_dict['picsaftertrigger'][2]
        else:
            picsaftertrigger = numpics
        framerate = self.camset.cam_dict['framerate'][2]
        if picsaftertrigger != 0:
            time.sleep(picsaftertrigger/framerate)
        self.display_timer.stop()
        self.stop()

    def _get_img(self, index):
        #Get img from index of buffer
        img_ptr = SISO.Fg_getImagePtrEx(self.fg, int(index), 0, self.memHandle)
        nImg = SISO.getArrayFrom(img_ptr, self.camset.cam_dict['frameformat'][2][2],
                                 self.camset.cam_dict['frameformat'][2][3])
        return gray_to_bgr(nImg)

    def stop(self):
        SISO.Fg_stopAcquire(self.fg, 0)

    def display_img(self):
        #Displays img in buffer
        cur_pic_nr = SISO.Fg_getLastPicNumberEx(self.fg, 0, self.memHandle)
        win_name_img = "Source Image (SiSo Runtime)"
        # get image pointer
        img_ptr = SISO.Fg_getImagePtrEx(self.fg, cur_pic_nr, 0, self.memHandle)
        SISO.DrawBuffer(self.display, img_ptr, cur_pic_nr, win_name_img)
        return cur_pic_nr

    def close_display(self):
        SISO.CloseDisplay(self.display)
        #os.system('wmctrl -a "Display"')
        #os.system('wmctrl -c "Display"')

    def reset_display(self):
        self.stop()
        self.display_timer.stop()
        self.close_display()
        time.sleep(0.1)

    def save_vid(self, startframe=None, stopframe=None, ext='.mp4'):
        print('saving video...')
        if startframe is None:
            startframe = 1
        elif startframe == 0:
            startframe = 1
        if stopframe is None:
            stopframe = self.numpics
        elif stopframe > self.numpics:
            stopframe = self.numpics
            print('changing stopframe to maximum value')

        date_time = self._datetimestr()
        filename_op = self.filename_base+str(date_time)+ext

        writevid = WriteVideo(filename=filename_op, frame_size=np.shape(self._get_img(1)))

        for frame in range(startframe, stopframe, 1):
            nImg = self._get_img(frame)
            writevid.add_frame(nImg)
        writevid.close()
        print('Finished writing video')

    def _datetimestr(self):
        now = time.gmtime()
        return time.strftime("%Y%m%d_%H%M%S", now)


class DisplayTimer(object):
    def __init__(self, interval, startfunction):
        self._timer     = None
        self.interval   = interval
        self.startfunction   = startfunction
        #self.stopfunction = stopfunction
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()

    def start(self):
        self.startfunction()
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False




if __name__ == '__main__':
    from cam_settings import CameraSettings

    cam=Camera()
    cam.initialise()
    cam.camset.write_single_cam_command('framerate',100)
    cam.camset.write_single_cam_command('exptime', 5000)
    cam.camset.save_config('current.ccf')
    cam.grab()
    #cam.preview()
    cam.trigger(numpics=2000)
    cam.save_vid()
    cam.close_display()

