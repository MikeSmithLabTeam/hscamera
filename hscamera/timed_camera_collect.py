from threading import Timer
from microscope.camerahs import Camera


def collect_movie(filename=None, numpics=None):
    cam = Camera(filename=filename)
    cam.initialise()
    cam.set_autosave(True)
    cam.grab(numpics=numpics)
    cam.resource_cleanup()
    cam.close_display()
    del cam






class CameraTimer(object):
    def __init__(self, interval=60, numpics=50, nummovies=2, filename=None, startfunction=None):
        self._timer     = None
        self.interval   = interval
        self.numpics = numpics
        self.nummovies = nummovies
        self.filename = filename
        self.startfunction   = startfunction
        #self.stopfunction = stopfunction
        self.counter=0
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()


    def start(self):
        self.startfunction(filename=self.filename, numpics=self.numpics)

        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

        self.counter += 1
        if self.counter >= self.nummovies:
            self.stop()

    def stop(self):
        self._timer.cancel()
        self.is_running = False

if __name__ == '__main__':
    #CameraTimer(Interval in sec, Numpics per collection, NumMovies, Filename base, function to handle collection)
    timed_collect = CameraTimer(interval=60, numpics=50, nummovies=2, filename='/home/ppzmis/Videos/test.mp4', startfunction=collect_movie)