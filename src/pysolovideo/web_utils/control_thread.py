from threading import Thread
from pysolovideo.tracking.monitor import Monitor

# Interface to V4l
from pysolovideo.tracking.cameras import V4L2Camera
from pysolovideo.tracking.cameras import MovieVirtualCamera

# Build ROIs from greyscale image
from pysolovideo.tracking.roi_builders import SleepMonitorWithTargetROIBuilder

# the robust self learning tracker
from pysolovideo.tracking.trackers import AdaptiveBGModel

class ControlThread(Thread):

    def __init__(self, *args, **kwargs):

        cam = MovieVirtualCamera('../Projects/13_003_sleep depriation machine/sleepMonitor_5days.avi')
        #cam = V4L2Camera(0, target_fps=5, target_resolution=(560, 420))

        roi_builder = SleepMonitorWithTargetROIBuilder()

        rois = roi_builder(cam)

        self._monit = Monitor(cam,
                    AdaptiveBGModel,
                    rois,
                    out_file=machine_id+'out', # save a csv out
                    )

        super(ControlThread, self).__init__()

    def run(self, **kwarg):

        self._monit.run()

    def stop(self):
        self._monit.stop()

    @property
    def last_frame(self):
        return self._monit.last_frame

    @property
    def data_history(self):
        return self._monit.data_history