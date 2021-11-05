import sys

sys.path.append("/opt/SiliconSoftware/Runtime5.7.0/SDKWrapper/PythonWrapper/python36/bin")
sys.path.append("/opt/SiliconSoftware/Runtime5.7.0/lib64")

import SiSoPyInterface as SISO
import pexpect

import time

from threading import Timer
from labvision.video import WriteVideo
from labvision.images import gray_to_bgr
import numpy as np

import cv2

class Camera:

    config_dir = '/opt/ConfigFiles/'
    mcf_filename = config_dir + 'current.mcf'
    filename_base = '/home/ppxjd3/Videos/'

    def __init__(self):

        # Not Really sure why I have both of these lines
        self.frame_grabber = SISO.Fg_InitConfig(self.mcf_filename, 0)
         # self.print_all_framegrabber_parameters()
        SISO.Fg_loadConfig(self.frame_grabber, self.mcf_filename)

        self.setup_camera_com()

        self.gain = 2
        self.set_gain(self.gain)

        self.fpn_correction = 1
        self.set_fpn_correction(self.fpn_correction)

        self.width = 1280
        self.height = 1024
        self.set_width_and_height(self.width, self.height)

        self.framerate = 30
        self.set_framerate(self.framerate)

        self.exposure = 5000
        self.set_exposure(self.exposure)

    def set_fpn_correction(self, value):
        assert value in [0, 1], 'Value must be 0 or 1'
        self.fpn_correction = value
        self.send_camera_command('#F('+str(self.fpn_correction)+')')

    def set_gain(self, value):
        assert value in [1, 1.5, 2, 2.25, 3, 4], 'Value must be in [1, 1.5, 2, 2.25, 3, 4]'
        self.gain = value
        self.send_camera_command('#G('+str(self.gain)+')')

    def set_exposure(self, value):
        max_exposure = self.get_max_exposure()
        if value > max_exposure:
            print("value of ", value, " is too high, setting to maximum value of ", max_exposure)
            self.exposure = max_exposure
        else:
            self.exposure = value

        self.send_camera_command('#e('+str(self.exposure)+')')

    def get_max_exposure(self):
        result = self.send_camera_command('#a', True)
        return int(result)  # has a byte before and after the number

    def set_width_and_height(self, width, height):
        assert ((width%16==0) and (width%24==0)) or (width==1280), 'Frame width must be divisible by 16 and 24 or 1280'
        assert (height%2 == 0) and (height <=1024), 'Frame height must be divisible by 2 and at most 1024'
        self.width = width
        self.height = height
        self.send_camera_command('#R('+str(self.width)+','+str(self.height)+')')
        width_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_WIDTH')
        height_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_HEIGHT')
        SISO.Fg_setParameterWithInt(self.frame_grabber, height_id, self.height, 0)
        SISO.Fg_setParameterWithInt(self.frame_grabber, width_id, self.width, 0)

    def set_framerate(self, value):
        self.framerate = value
        self.send_camera_command('#r('+str(value)+')')
        framerate_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_FRAMESPERSEC')
        SISO.Fg_setParameterWithDouble(self.frame_grabber, framerate_id, self.framerate, 0)

    def setup_camera_com(self):
        command = '/opt/SiliconSoftware/Runtime5.7.0/bin/clshell -a -i'
        self.camera_com = pexpect.spawn(command)
        for f in range(5):
            self.camera_com.readline()

    def send_camera_command(self, command, expect_return_value=False):
        self.camera_com.sendline(command.encode())
        input_line = self.camera_com.readline()
        if expect_return_value:
            result = self.camera_com.readline()
            return result[1:-4]
        else:
            result = self.camera_com.readline()
            return None

    def initialise(self):
        buffer_size = self.width * self.height * 1000
        self.mem_handle = SISO.Fg_AllocMemEx(self.frame_grabber, buffer_size, 1000)
        self.display = SISO.CreateDisplay(8, self.width, self.height)
        SISO.SetBufferWidth(self.display, self.width, self.height)

    def preview(self):
        self.grab()
        self.trigger(numpics=1000)
        self.close_display()

    def close_display(self):
        SISO.CloseDisplay(self.display)

    def grab(self):
        self.numpics = SISO.GRAB_INFINITE
        err = SISO.Fg_AcquireEx(self.frame_grabber, 0, self.numpics, SISO.ACQ_STANDARD, self.mem_handle)

        self.display_timer = DisplayTimer(0.03, self.display_img)
        self.display_timer.start()

    def _get_img(self, index):
        #Get img from index of buffer
        img_ptr = SISO.Fg_getImagePtrEx(self.frame_grabber, int(index), 0, self.mem_handle)
        nImg = SISO.getArrayFrom(img_ptr, self.width, self.height)
        return gray_to_bgr(nImg)

    def display_img(self):
        # Displays img in buffer
        cur_pic_nr = SISO.Fg_getLastPicNumberEx(self.frame_grabber, 0, self.mem_handle)
        win_name_img = "Source Image (SiSo Runtime)"
        # get image pointer
        img_ptr = SISO.Fg_getImagePtrEx(self.frame_grabber, cur_pic_nr, 0, self.mem_handle)
        SISO.DrawBuffer(self.display, img_ptr, cur_pic_nr, win_name_img)
        return cur_pic_nr

    def trigger(self,numpics=None):
        self.numpics = numpics
        framerate = self.framerate
        time.sleep(numpics/framerate)
        self.display_timer.stop()
        self.stop()

    def stop(self):
        SISO.Fg_stopAcquire(self.frame_grabber, 0)

    def print_all_framegrabber_parameters(self):
        for f in range(86):
            name = SISO.Fg_getParameterName(self.frame_grabber, f)
            id = SISO.Fg_getParameterIdByName(self.frame_grabber, name)
            value = SISO.Fg_getParameterWithInt(self.frame_grabber, id, 0)
            print(f, name, id, value)

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
        filename_op = self.filename_base + str(date_time) + ext

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
        self._timer = None
        self.interval = interval
        self.startfunction = startfunction
        # self.stopfunction = stopfunction
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
    cam = Camera()
    cam.initialise()
    cam.preview()
    # cam.grab()
    # cam.trigger(1000)
    # cam.save_vid()