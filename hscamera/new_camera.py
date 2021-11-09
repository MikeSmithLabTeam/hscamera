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
import json

default_settings = {
    'gain': 2,
    'width': 1280,
    'height': 1024,
    'framerate': 30,
    'exposure': 5000,
    'fpn_correction': 1,
    'blacklevel': 100
}

with open('/opt/ConfigFiles/default_settings.json', 'w') as f:
    json.dump(default_settings, f)



class Camera:

    config_dir = '/opt/ConfigFiles/'
    mcf_filename = config_dir + 'current.mcf' # If this file doesn't exist make it using microDisplayX
    filename_base = '/home/ppxjd3/Videos/'

    def __init__(self, settings_file=None, window=True):
        if settings_file is None:
            self.settings = default_settings
        else:
            with open(settings_file, 'r') as f:
                self.settings = json.load(f)

        self.ready = False
        # Not Really sure why I have both of these lines
        self.frame_grabber = SISO.Fg_InitConfig(self.mcf_filename, 0)
         # self.print_all_framegrabber_parameters()
        SISO.Fg_loadConfig(self.frame_grabber, self.mcf_filename)

        self.numpics = 1000

        self.setup_camera_com()

        self.setup_initial_settings()

        self.initialise_buffer()

        self.ready = True


        if window:
            self.initialise_window()

    def setup_initial_settings(self):
        self.set_gain(self.settings['gain'])
        self.set_fpn_correction(self.settings['fpn_correction'])
        self.set_width_and_height(self.settings['width'], self.settings['height'])
        self.set_framerate(self.settings['framerate'])
        self.set_exposure(self.settings['exposure'])
        self.set_blacklevel(self.settings['blacklevel'])

    def set_blacklevel(self, value):
        assert (value >= 0) and (value <=255), 'Blacklevel must be between 0 and 255'
        self.settings['blacklevel'] = value
        self.send_camera_command('#z('+str(value)+')')

    def set_fpn_correction(self, value):
        assert value in [0, 1], 'Value must be 0 or 1'
        self.settings['fpn_correction'] = value
        self.send_camera_command('#F('+str(value)+')')

    def set_gain(self, value):
        assert value in [1, 1.5, 2, 2.25, 3, 4], 'Value must be in [1, 1.5, 2, 2.25, 3, 4]'
        self.settings['gain'] = value
        command = '#G('+str(value)+')'
        self.send_camera_command(command)

    def set_exposure(self, value):
        max_exposure = self.get_max_exposure()
        if value > max_exposure:
            print("value of ", value, " is too high, setting to maximum value of ", max_exposure)
            self.settings['exposure'] = max_exposure
        else:
            self.settings['exposure'] = value

        self.send_camera_command('#e('+str(self.settings['exposure'])+')')

    def get_max_exposure(self):
        result = self.send_camera_command('#a', True)
        return int(result)  # has a byte before and after the number

    def get_max_framerate(self):
        result = self.send_camera_command('#A', True)
        return int(result)

    def set_width_and_height(self, width, height):
        assert ((width%16==0) and (width%24==0)) or (width==1280), 'Frame width must be divisible by 16 and 24 or 1280'
        assert (height%2 == 0) and (height <=1024), 'Frame height must be divisible by 2 and at most 1024'
        self.settings['width'] = width
        self.settings['height'] = height
        self.send_camera_command('#R('+str(width)+','+str(height)+')')
        width_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_WIDTH')
        height_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_HEIGHT')
        SISO.Fg_setParameterWithInt(self.frame_grabber, height_id, height, 0)
        SISO.Fg_setParameterWithInt(self.frame_grabber, width_id, width, 0)

    def set_height(self, height):
        assert (height%2 == 0) and (height <=1024), 'Frame height must be divisible by 2 and at most 1024'
        self.settings['height'] = height
        self.send_camera_command('#R(+'+str(self.settings['width'])+','+str(height)+')')
        self.stop()
        height_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_HEIGHT')
        SISO.Fg_setParameterWithInt(self.frame_grabber, height_id, height, 0)
        self.start()

    def set_width(self, width):
        assert (width % 16 == 0), 'Frame height must be divisible by 2 and at most 1024'
        self.settings['width'] = width
        self.send_camera_command('#R(+' + str(width) + ',' + str(self.settings['height']) + ')')
        self.stop()
        width_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_WIDTH')
        SISO.Fg_setParameterWithInt(self.frame_grabber, width_id, width, 0)
        self.start()

    def set_framerate(self, value):
        self.settings['framerate'] = value
        self.send_camera_command('#r('+str(value)+')')

    def setup_camera_com(self):
        command = '/opt/SiliconSoftware/Runtime5.7.0/bin/clshell -a -i'
        self.camera_com = pexpect.spawn(command)
        for f in range(5):
            self.camera_com.readline()

    def send_camera_command(self, command, expect_return_value=False):
        self.camera_com.sendline(command.encode())
        input_line = self.camera_com.readline()
        if expect_return_value:
            result = self.camera_com.readline().decode().strip()
            if result[0] == '>':
                return result[1:-1]
            else:
                return result[:-1]
        else:
            result = self.camera_com.readline()
            return None

    def initialise_buffer(self):
        buffer_size = self.settings['width'] * self.settings['height'] * 1000
        # Reserves an aera of the main memory as frame buffer, blocks it and makes it available for the user
        self.mem_handle = SISO.Fg_AllocMemEx(self.frame_grabber, buffer_size, 1000)

    def initialise_window(self):
        # Creates a display window
        self.display = SISO.CreateDisplay(8, self.settings['width'], self.settings['height'])
        # Configures the size of the frame buffer, allowing a window smaller than the frame buffer?
        SISO.SetBufferWidth(0, self.settings['width'], self.settings['height'])

    def close_display(self):
        SISO.CloseDisplay(self.display)

    def start(self):
        self.numpics = SISO.GRAB_INFINITE
        # Starts continuous grabbing in background.
        err = SISO.Fg_AcquireEx(self.frame_grabber, 0, self.numpics, SISO.ACQ_STANDARD, self.mem_handle)

    def get_current_img(self):
        index = SISO.Fg_getLastPicNumberEx(self.frame_grabber, 0, self.mem_handle)
        ptr = SISO.Fg_getImagePtrEx(self.frame_grabber, index, 0, self.mem_handle)
        im = SISO.getArrayFrom(ptr, self.settings['width'], self.settings['height'])
        return gray_to_bgr(im)

    def display_img(self):
        # Displays img in buffer
        cur_pic_nr = SISO.Fg_getLastPicNumberEx(self.frame_grabber, 0, self.mem_handle)
        win_name_img = "Source Image (SiSo Runtime)"
        # get image pointer
        img_ptr = SISO.Fg_getImagePtrEx(self.frame_grabber, cur_pic_nr, 0, self.mem_handle)
        SISO.DrawBuffer(self.display, img_ptr, cur_pic_nr, win_name_img)
        return cur_pic_nr

    def stop(self):
        SISO.Fg_stopAcquire(self.frame_grabber, 0)

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



if __name__ == '__main__':
    cam = Camera('/opt/ConfigFiles/default_settings.json')
    cam.grab()
    cam.trigger(100)