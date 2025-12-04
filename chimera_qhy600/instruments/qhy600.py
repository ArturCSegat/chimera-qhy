import datetime as dt
import time

import numpy as np
from chimera.core.event import event
from chimera.core.lock import lock
from chimera.instruments.camera import CameraBase
from chimera.interfaces.camera import CCD, CameraStatus, ReadoutMode
from qhy600mdriver import QHY600MDriver


class QHY600(CameraBase):
    """QHY600 camera as a Chimera instrument."""

    __config__ = {
        "ccd_width": 9600,
        "ccd_height": 6422,
        "pixel_width": 3.76,
        "pixel_height": 3.76,
    }

    def __init__(self):
        super().__init__()
        self["device"] = "USB"
        self._current_ccd = 1 << 1
        self._current_adc = 1 << 2
        self._current_readout_mode = 1 << 3
        self._ccds = {self._current_ccd: CCD.IMAGING}
        self._adcs = {"16 bit": self._current_adc}
        self._binnings = {"1x1": self._current_readout_mode}
        self._binning_factors = {
            "1x1": 1,
            "2x2": 2,
            "3x3": 3,
            "4x4": 4,
        }
        self._last_frame_start = 0

        # TODO reference: https://www.qhyccd.com/astronomical-camera-qhy600/#:~:text=Readout%20Mode%20%230%20(Photographic%20Mode)
        readout_mode = ReadoutMode()
        readout_mode.mode = 1
        readout_mode.gain = 10
        readout_mode.width = 9600
        readout_mode.height = 6422
        readout_mode.pixel_width = 3.76
        readout_mode.pixel_height = 3.76
        self._readout_modes = {
            self._current_ccd: {self._current_readout_mode: readout_mode}
        }
        self.drv = QHY600MDriver(self.log)

    @lock
    def __start__(self):
        self.drv.open()

    @lock
    def __stop__(self):
        self.drv.close()

    def is_cooling(self):
        return False

    def is_fanning(self):
        return False  # TODO

    @lock
    def get_temperature(self):
        return self.drv.get_temperature()

    def supports(self, feature=None):
        return False  # TODO

    def get_ccds(self):
        return self._ccds

    def get_current_ccd(self):
        return self._current_ccd

    def get_adcs(self):
        return self._adcs

    def get_physical_size(self):
        return (self["ccd_width"], self["ccd_height"])

    def get_pixel_size(self):
        return (self["pixel_width"], self["pixel_height"])

    def get_overscan_size(self, ccd=None):
        return (
            0,
            0,
        )  # TODO is it possible to set this value in the QHY600? Because it returned 0 x 0 in the SDK.

    def get_binnings(self):
        return self._binnings

    def get_readout_modes(self):
        return self._readout_modes

    def _expose(self, image_request):
        self.expose_begin(image_request)

        status = CameraStatus.OK

        self.drv.start_exposure(int(image_request["exptime"]))

        t = 0
        self._last_frame_start = dt.datetime.utcnow()
        while t < image_request["exptime"]:
            if self.abort.is_set():
                status = CameraStatus.ABORTED
                break

            time.sleep(0.1)
            t += 0.1

        self.expose_complete(image_request, status)

    def _readout(self, image_request):
        (mode, binning, top, left, width, height) = self._get_readout_mode_info(
            image_request["binning"], image_request["window"]
        )

        self.readout_begin(image_request)

        try:
            # img = self.get_fake_image(width, height)
            img = self.drv.start_readout(mode.mode, top, left, width, height)
        except Exception as e:
            self.log.error(f"Error during readout: {e}")
            self.readout_complete(None, CameraStatus.ABORTED)
            return None

        proxy = self._save_image(
            image_request,
            img,
            {
                "frame_start_time": self._last_frame_start,
                "frame_temperature": self.get_temperature(),
                "binning_factor": self._binning_factors[binning],
            },
        )

        self.readout_complete(proxy, CameraStatus.OK)

        return proxy

    def get_fake_image(self, width, height):
        with open("/home/vlm/tmp/imagem_via_SDK_byte-array.raw", "rb") as raw_file:
            raw_data = raw_file.read()

        # Convert the byte data to a NumPy array
        image_array = np.frombuffer(raw_data, dtype=np.uint16)

        # Reshape the array to the CCD dimensions
        try:
            # img = np.zeros((height, width), np.int32) # placeholder for actual image data
            img = image_array.reshape((height, width))
        except ValueError:
            self.log.warning("Trying alternative orientation...")
            img = image_array.reshape((width, height)).T

        return img
