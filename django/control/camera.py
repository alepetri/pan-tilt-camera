"""
Based on Marcelo Rovai's work here: https://github.com/Mjrovai/Video-Streaming-with-Flask/blob/master/camWebServer/camera_pi.py
"""

import time
import io
import threading
from picamera2 import Picamera2
from libcamera import Transform, controls # type: ignore

from enum import Enum

class Camera:
    class ZoomState(Enum):
        NONE = 1
        ZOOM_IN = 2
        ZOOM_OUT = 3

    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    last_access = 0  # time of last client access to the camera
    zoom_state: ZoomState = ZoomState.NONE

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

    def zoom(self, zoom_cmd: ZoomState):
        Camera.last_access = time.time()
        self.initialize()
        if Camera.zoom_state == Camera.ZoomState.NONE:
            Camera.zoom_state = zoom_cmd

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

            # https://github.com/raspberrypi/picamera2/blob/main/examples/zoom.py
            size_px = list(camera.capture_metadata()['ScalerCrop'][2:4]) # type: ignore
            full_size_px = list(camera.camera_properties['PixelArraySize'])

            data = io.BytesIO()
            while time.time() - cls.last_access < 10:
                camera.capture_metadata()

                if cls.zoom_state == cls.ZoomState.ZOOM_IN:
                    size_px = [int(s * 0.95) for s in size_px]
                elif cls.zoom_state == cls.ZoomState.ZOOM_OUT:
                    size_px = [int(s * 1.05) for s in size_px]
                
                if cls.zoom_state != cls.ZoomState.NONE:
                    if any(s > r for r, s in zip(full_size_px, size_px)):
                        size_px = full_size_px.copy()
                    offset_px = [(r - s) // 2 for r, s in zip(full_size_px, size_px)]
                    camera.set_controls({'ScalerCrop': offset_px + size_px})
                    cls.zoom_state = cls.ZoomState.NONE

                # store frame
                camera.capture_file(data, format='jpeg')

                data.seek(0)
                cls.frame = data.read()

                # reset stream for next frame
                data.seek(0)
                data.truncate()

        print("Stopping Camera!")
        
        cls.thread = None