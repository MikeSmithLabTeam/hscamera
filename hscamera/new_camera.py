import sys

sys.path.append("/opt/SiliconSoftware/Runtime5.7.0/SDKWrapper/PythonWrapper/python36/bin")
sys.path.append("/opt/SiliconSoftware/Runtime5.7.0/lib64")

import SiSoPyInterface as SISO
import pexpect

import time

from labvision.video import WriteVideo
from labvision.images import gray_to_bgr, load
import numpy as np
import json

default_settings = {
    'gain': 2,
    'width': 1280,
    'height': 1024,
    'framerate': 30,
    'exposure': 15000,
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
        self.started = False
        self.no_image = load('no_image.jpg')
        # Not Really sure why I have both of these lines
        self.frame_grabber = SISO.Fg_InitConfig(self.mcf_filename, 0)
         # self.print_all_framegrabber_parameters()
        SISO.Fg_loadConfig(self.frame_grabber, self.mcf_filename)

        self.setup_camera_com()

        self.setup_initial_settings()

        self.initialise_buffer()

        self.ready = True


        if window:
            self.initialise_window()

    def setup_initial_settings(self):
        self.set_gain(self.settings['gain'])
        self.set_fpn_correction(self.settings['fpn_correction'])
        self.set_width(self.settings['width'])
        self.set_height(self.settings['height'])
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

    def set_height(self, height):
        assert (height%2 == 0) and (height <=1024), 'Frame height must be divisible by 2 and at most 1024'
        self.settings['height'] = height
        self.send_camera_command('#R(+'+str(self.settings['width'])+','+str(height)+')')
        if self.started:
            self.stop()
        height_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_HEIGHT')
        SISO.Fg_setParameterWithInt(self.frame_grabber, height_id, height, 0)
        if self.ready:
            self.start()

    def set_width(self, width):
        assert (width % 16 == 0), 'Frame height must be divisible by 2 and at most 1024'
        self.settings['width'] = width
        self.send_camera_command('#R(+' + str(width) + ',' + str(self.settings['height']) + ')')
        if self.started:
            self.stop()
        width_id = SISO.Fg_getParameterIdByName(self.frame_grabber, 'FG_WIDTH')
        SISO.Fg_setParameterWithInt(self.frame_grabber, width_id, width, 0)
        if self.ready:
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

    def initialise_buffer(self, numpics=1000):
        self.numpics = numpics
        buffer_size = self.settings['width'] * self.settings['height'] * numpics
        # Reserves an aera of the main memory as frame buffer, blocks it and makes it available for the user
        self.mem_handle = SISO.Fg_AllocMemEx(self.frame_grabber, buffer_size, numpics)

    def initialise_window(self):
        # Creates a display window
        self.display = SISO.CreateDisplay(8, self.settings['width'], self.settings['height'])
        # Configures the size of the frame buffer, allowing a window smaller than the frame buffer?
        SISO.SetBufferWidth(0, self.settings['width'], self.settings['height'])

    def close_display(self):
        SISO.CloseDisplay(self.display)

    def start(self, numpics=None):
        if self.started:
            self.stop()
            self.clear_buffer()
        if numpics is None:
            numpics = SISO.GRAB_INFINITE
            self.initialise_buffer(1000)
        else:
            self.initialise_buffer(numpics)

        # Starts continuous grabbing in background.
        err = SISO.Fg_AcquireEx(self.frame_grabber, 0, numpics, SISO.ACQ_STANDARD, self.mem_handle)
        self.started = True

    def get_current_img(self):
        index = SISO.Fg_getLastPicNumberEx(self.frame_grabber, 0, self.mem_handle)
        if index == 0:  # no picture in buffer yet
            return self.no_image
        else:
            return self.get_img(index)

    def get_img(self, index):
        ptr = SISO.Fg_getImagePtrEx(self.frame_grabber, index, 0, self.mem_handle)
        im = SISO.getArrayFrom(ptr, self.settings['width'], self.settings['height'])
        return gray_to_bgr(im)

    def stop(self):
        SISO.Fg_stopAcquire(self.frame_grabber, 0)
        self.started = False

    def clear_buffer(self):
        SISO.Fg_FreeMemEx(self.frame_grabber, self.mem_handle)

    def save_vid(self, filename=None):
        date_time = self._datetimestr()
        if filename is None:
            filename = self.filename_base + str(date_time) + '.MP4'

        writevid = WriteVideo(filename=filename, frame_size=np.shape(self.get_current_img()))

        for frame in range(1, self.numpics, 1):
            nImg = self.get_img(frame)
            writevid.add_frame(nImg)
        writevid.close()
        print('Finished writing video')
        self.clear_buffer()
        self.start()

    def _datetimestr(self):
        now = time.gmtime()
        return time.strftime("%Y%m%d_%H%M%S", now)