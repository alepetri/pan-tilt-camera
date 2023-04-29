"""
Based on Marcelo Rovai's work here: https://github.com/Mjrovai/Video-Streaming-with-Flask/blob/master/camWebServer/camera_pi.py
"""

import time
import io
import threading
from picamera2 import Picamera2
from libcamera import Transform, controls # type: ignore

class Camera:
    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    last_access = 0  # time of last client access to the camera

    def initialize(self):
        if Camera.thread is None:
            # start background frame thread
            Camera.thread = threading.Thread(target=self._thread) # type: ignore
            Camera.thread.start()

            # wait until frames start to be available
            while self.frame is None:
                time.sleep(0)

    def get_frame(self):
        Camera.last_access = time.time()
        self.initialize()
        return self.frame

    @classmethod
    def _thread(cls):
        print("Starting Camera!")
        with Picamera2() as camera:
            # camera setup
            config = camera.create_video_configuration(transform=Transform(vflip=True, hflip=True))
            camera.configure(config) # type: ignore
            camera.set_controls({"AfMode": controls.AfModeEnum.Continuous})

            camera.start()

            # let camera warm up
            time.sleep(2)

            data = io.BytesIO()
            while time.time() - cls.last_access < 10:
                # store frame
                camera.capture_file(data, format='jpeg')

                data.seek(0)
                cls.frame = data.read()

                # reset stream for next frame
                data.seek(0)
                data.truncate()

        print("Stopping Camera!")
        
        cls.thread = None