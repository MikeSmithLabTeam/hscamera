import sys
import logging

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
    'width': 1024,
    'height': 1024,
    'framerate': 30,
    'exposure': 15000,
    'fpn_correction': 1,
    'blacklevel': 100,
    'dualslope': 0,
    'tripleslope': 0,
    'dualslope_time': 1,
    'tripleslope_time': 1,

    'x': 0,
    'y': 0
}

with open('/opt/ConfigFiles/default_settings.json', 'w') as f:
    json.dump(default_settings, f)



class Camera:

    config_dir = '/opt/ConfigFiles/'
    mcf_filename = config_dir + 'current.mcf' # If this file doesn't exist make it using microDisplayX
    filename_base = '/home/ppxjd3/Videos/'

    def __init__(self, settings_file=None):

        self.settings = self.load_settings(settings_file)

        self.ready = False
        self.started = False

        self.no_image = load('no_image.jpg')
        # Not Really sure why I have both of these lines

        logging.info('Initialising framegrabber with mcf file')
        self.frame_grabber = SISO.Fg_InitConfig(self.mcf_filename, 0)
        SISO.Fg_loadConfig(self.frame_grabber, self.mcf_filename)

        self.setup_camera_com()

        self.setup_initial_settings()

        self.ready = True

    def load_settings(self, filename):
        if filename is None:
            logging.info('Loading default settings')
            settings = default_settings
        else:
            logging.info('Loading settings from {}'.format(filename))
            with open(filename, 'r') as f:
                settings = json.load(f)
        return settings

    def load_new_settings(self, filename):
        self.settings = self.load_settings(filename)
        self.setup_initial_settings()

    def save_settings(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.settings, f)

    def setup_initial_settings(self):
        logging.info('Setting intial parameters from dictionary')
        self.set_gain(self.settings['gain'])
        self.set_fpn_correction(self.settings['fpn_correction'])
        self.set_width(self.settings['width'])
        self.set_height(self.settings['height'])
        self.set_framerate(self.settings['framerate'])
        self.set_exposure(self.settings['exposure'])
        self.set_blacklevel(self.settings['blacklevel'])
        self.set_x(self.settings['x'])
        self.set_y(self.settings['y'])
        self.set_dualslope_state(self.settings['dualslope'])
        self.set_dualslope_time(self.settings['dualslope_time'])
        self.set_tripleslope_state(self.settings['tripleslope'])
        self.set_tripleslope_time(self.settings['tripleslope_time'])

    def set_dualslope_state(self, value):
        assert (value == 1) or (value == 0), 'Value must be 0 or 1'
        logging.debug('dualslope set to {}'.format(value))
        self.settings['dualslope'] = value
        self.send_camera_command('#D{}'.format(value))

    def set_dualslope_time(self, value):
        assert (value >= 1) and (value <= self.settings['exposure']), 'Value must be between 1 and the exposure time'
        logging.debug('dualslope_time set to {}'.format(value))
        self.settings['dualslope_time'] = value
        self.send_camera_command('#d{}'.format(value))

    def set_tripleslope_state(self, value):
        assert (value == 1) or (value == 0), 'Value must be 0 or 1'
        logging.debug('tripleslope set to {}'.format(value))
        self.settings['tripleslope'] = value
        self.send_camera_command('#T{}'.format(value))

    def set_tripleslope_time(self, value):
        assert (value >= 1) and (value <= self.settings['dualslope_time']), 'Value must be between 1 and the dualslope time'
        logging.debug('tripleslope_time set to {}'.format(value))
        self.settings['tripleslope_time'] = value
        self.send_camera_command('#t{}'.format(value))

    def set_blacklevel(self, value):
        assert (value >= 0) and (value <=255), 'Blacklevel must be between 0 and 255'
        logging.debug('blacklevel set to {}'.format(value))
        self.settings['blacklevel'] = value
        self.send_camera_command('#z('+str(value)+')')

    def set_fpn_correction(self, value):
        assert value in [0, 1], 'Value must be 0 or 1'
        logging.debug('fpn_correction set to {}'.format(value))
        self.settings['fpn_correction'] = value
        self.send_camera_command('#F('+str(value)+')')

    def set_gain(self, value):
        assert value in [1, 1.5, 2, 2.25, 3, 4], 'Value must be in [1, 1.5, 2, 2.25, 3, 4]'
        logging.debug('gain set to {}'.format(value))
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
        logging.debug('Exposure set to {}'.format(self.settings['exposure']))
        self.send_camera_command('#e('+str(self.settings['exposure'])+')')

    def get_max_exposure(self):
        result = self.send_camera_command('#a', True)
        return int(result)  # has a byte before and after the number

    def get_max_framerate(self):
        result = self.send_camera_command('#A', True)
        return int(result)

    def set_height(self, height):
        assert (height%2 == 0) and (height <=1024), 'Frame height must be divisible by 2 and at most 1024'
        logging.debug('Height set to {}'.format(height))
        self.settings['height'] = height
        self.send_camera_command('#R({},{},{},{})'.format(self.settings['x'], self.settings['y'], self.settings['width'], self.settings['height']))

    def set_width(self, width):
        assert (width % 16 == 0) and (width <= 1024), 'Frame height must be divisible by 2 and at most 1024'
        logging.debug('Width set to {}'.format(width))
        self.settings['width'] = width
        self.send_camera_command('#R({},{},{},{})'.format(self.settings['x'], self.settings['y'], self.settings['width'], self.settings['height']))

    def set_x(self, x):
        logging.debug('x set to {}'.format(x))
        self.settings['x'] = x
        self.send_camera_command('#R({},{},{},{})'.format(self.settings['x'], self.settings['y'], self.settings['width'], self.settings['height']))

    def set_y(self, y):
        logging.debug('y set to {}'.format(y))
        self.settings['y'] = y
        self.send_camera_command(
            '#R({},{},{},{})'.format(self.settings['x'], self.settings['y'], self.settings['width'],
                                     self.settings['height']))

    def set_framerate(self, value):
        logging.debug('framerate set to {}'.format(value))
        self.settings['framerate'] = value
        self.send_camera_command('#r('+str(value)+')')

    def setup_camera_com(self):
        logging.debug('Camera communication initialised')
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

    def get_max_numpics(self):
        # Maximum buffer size is just over 4GB so make sure buffer is less than 4GB
        num_bytes_im = self.settings['width'] * self.settings['height']
        num_ims = int(4e9//num_bytes_im)
        return num_ims


    def initialise_buffer(self, numpics=None):
        if numpics is None:
            numpics = self.get_max_numpics()

        self.numpics = numpics
        buffer_size = self.settings['width'] * self.settings['height'] * numpics
        logging.debug('Initialising buffer of size {} GB'.format(buffer_size/1e9))
        # Reserves an aera of the main memory as frame buffer, blocks it and makes it available for the user
        self.mem_handle = SISO.Fg_AllocMemEx(self.frame_grabber, buffer_size, numpics)
        logging.info('Buffer initialised')

    def start(self, numpics=None):
        if self.started:
            self.stop()
            self.clear_buffer()
        if numpics is None:
            numpics = SISO.GRAB_INFINITE
            self.initialise_buffer()
        else:
            self.initialise_buffer(numpics)

        # Starts continuous grabbing in background.
        err = SISO.Fg_AcquireEx(self.frame_grabber, 0, numpics, SISO.ACQ_STANDARD, self.mem_handle)
        logging.info('Image acquisition started')
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
        logging.info('Image acquisition stopped')
        self.started = False

    def clear_buffer(self):
        SISO.Fg_FreeMemEx(self.frame_grabber, self.mem_handle)
        logging.info('Memory buffer cleared')

    def save_vid(self, filename=None, signal=None):
        date_time = self._datetimestr()
        if filename is None:
            filename = self.filename_base + str(date_time) + '.MP4'

        writevid = WriteVideo(filename=filename, frame_size=np.shape(self.get_current_img()))
        logging.info('Video writing started')
        for frame in range(1, self.numpics, 1):
            if signal is not None:
                signal(frame)
            nImg = self.get_img(frame)
            writevid.add_frame(nImg)
        writevid.close()
        logging.info('Video writing finished')
        # self.clear_buffer()
        self.start()

    def _datetimestr(self):
        now = time.gmtime()
        return time.strftime("%Y%m%d_%H%M%S", now)