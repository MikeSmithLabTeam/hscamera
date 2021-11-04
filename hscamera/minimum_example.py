import sys
import time

sys.path.append("/opt/SiliconSoftware/Runtime5.7.0/SDKWrapper/PythonWrapper/python36/bin")
sys.path.append("/opt/SiliconSoftware/Runtime5.7.0/lib64")
import SiSoPyInterface as SISO
import subprocess
from threading import Timer

cam_config_dir = '/opt/ConfigFiles/'
frame_grabber = SISO.Fg_InitConfig(cam_config_dir+'current.mcf', 0)
SISO.Fg_loadConfig(frame_grabber, cam_config_dir+'current.mcf')


def send_command(command):
    arguments = ['/opt/SiliconSoftware/Runtime5.7.0/bin/clshell', '-a', '-i']
    p = subprocess.Popen(arguments, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.stdin.write(command.encode())
    p.stdin.flush()
    stdout, stderr = p.communicate()
    stdout = stdout.splitlines()
    result = stdout[5]  # lines 0-4 are the preamble for the shell
    return result.decode()

def read_param_dict():
    with open('/opt/ConfigFiles/current.ccf', 'r') as f:
        content = f.read()
        return eval(content)

cam_dict = read_param_dict()



send_command('#G(5)')
max_exposure = send_command('#a')
print('max_exposure = ', max_exposure)

# send_command('e(1900)')
frameshape = (1280, 124)
send_command('#R(1280, 124)')

width_id = SISO.Fg_getParameterIdByName(frame_grabber, 'FG_WIDTH')
height_id = SISO.Fg_getParameterIdByName(frame_grabber, 'FG_HEIGHT')

SISO.Fg_setParameterWithInt(frame_grabber, width_id, frameshape[0], 0)
SISO.Fg_setParameterWithInt(frame_grabber, height_id, frameshape[1], 0)

SISO.Fg_saveConfig(frame_grabber, '/opt/ConfigFiles/new.mcf')

total_buffer_size = \
    frameshape[0] * \
    frameshape[1] * \
    cam_dict['numpicsbuffer'][2]

mem_handle = SISO.Fg_AllocMemEx(frame_grabber, total_buffer_size, cam_dict['numpicsbuffer'][2])
display = SISO.CreateDisplay(8, frameshape[0], frameshape[1])
SISO.SetBufferWidth(display, frameshape[0], frameshape[1])

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

numpics = 4000
err = SISO.Fg_AcquireEx(frame_grabber, 0, numpics, SISO.ACQ_STANDARD, mem_handle)
framerate = cam_dict['framerate'][2]

def display_im():
    cur_pic_nr = SISO.Fg_getLastPicNumberEx(frame_grabber, 0, mem_handle)
    window_name = "Source Image"
    img_ptr = SISO.Fg_getImagePtrEx(frame_grabber, cur_pic_nr, 0, mem_handle)
    SISO.DrawBuffer(display, img_ptr, cur_pic_nr, window_name)
    time.sleep(1/framerate)

timer = DisplayTimer(0.03, display_im)
timer.start()
time.sleep(numpics/framerate)
timer.stop()
SISO.Fg_stopAcquire(frame_grabber, 0)


