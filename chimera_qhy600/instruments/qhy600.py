from __future__ import annotations

import datetime as dt
import time

from chimera.core.lock import lock
from chimera.instruments.camera import CameraBase
from chimera.interfaces.camera import CameraFeature, CameraStatus, ReadoutMode

from qhy600mdriver import QHY600MDriver


class QHY600(CameraBase):
    """QHY600 camera as a Chimera instrument."""

    __config__ = {
        "ccd_width": 9600,
        "ccd_height": 6422,
        "pixel_width": 3.76,
        "pixel_height": 3.76,
        "sdk_library_path": None,
        "readout_mode_index": 0,
        "gain": 10.0,
        "fake": False,
    }

    def __init__(self):
        super().__init__()

        self["device"] = "USB"

        self._current_ccd = 1 << 1
        self._current_adc = 1 << 2

    @lock
    def __start__(self):
        self.log.info("Starting QHY600 camera")

        self._current_readout_mode = self["readout_mode_index"]

        self._adcs = {"16 bit": self._current_adc}
        self._binnings = {"1x1": self._current_readout_mode, "2x2": self._current_readout_mode, "3x3": self._current_readout_mode, "4x4": self._current_readout_mode}
        self._binning_factors = {"1x1": 1, "2x2": 2, "3x3": 3, "4x4": 4}

        self._last_frame_start: dt.datetime | None = None

        readout_mode = ReadoutMode()
        readout_mode.mode = int(self["readout_mode_index"])
        readout_mode.gain = float(self["gain"])
        readout_mode.width = int(self["ccd_width"])
        readout_mode.height = int(self["ccd_height"])
        readout_mode.pixel_width = float(self["pixel_width"])
        readout_mode.pixel_height = float(self["pixel_height"])
        self._readout_modes = {self._current_readout_mode: readout_mode}

        self.drv = QHY600MDriver(
            self.log,
            sdk_library_path=self["sdk_library_path"],
            readout_mode_index=int(self["readout_mode_index"]),
            gain=float(self["gain"]),
            use_mock_sdk=bool(self["fake"]),
        )

        self.drv.open()

        self._has_cooler = self.drv.has_cooler()
        self.log.info("Camera has cooler: %s", self._has_cooler)

    @lock
    def __stop__(self):
        self.log.info("Stopping QHY600 camera")
        self.drv.close()

    @lock
    def start_cooling(self, temp_c):
        self.drv.start_cooling(float(temp_c))
        return True

    @lock
    def stop_cooling(self):
        self.drv.stop_cooling()
        return True

    def is_cooling(self):
        return self.drv.is_cooling()

    @lock
    def get_temperature(self):
        return self.drv.get_temperature()

    @lock
    def get_set_point(self):
        return self.drv.get_set_point()

    def is_fanning(self):
        return self.drv.is_cooling()

    def supports(self, feature=None):
        if feature == CameraFeature.TEMPERATURE_CONTROL:
            return self._has_cooler
        return False

    def get_current_ccd(self):
        return self._current_ccd

    def get_adcs(self):
        return self._adcs

    def get_physical_size(self):
        return (self["ccd_width"], self["ccd_height"])

    def get_pixel_size(self):
        return (self["pixel_width"], self["pixel_height"])

    def get_overscan_size(self, ccd=None):
        return (0, 0)

    def get_binnings(self):
        return self._binnings

    def get_readout_modes(self):
        return self._readout_modes

    def _expose(self, image_request):
        self.expose_begin(image_request)

        exptime_s = float(image_request["exptime"])
        status = CameraStatus.OK

        (mode, binning, top, left, width, height) = self._get_readout_mode_info(
            image_request["binning"], image_request["window"]
        )
        bin_factor = self._binning_factors[binning]

        self.drv.start_exposure(
            exptime_s,
            bin_factor=bin_factor,
            roi=(left, top, width, height),
        )

        self._last_frame_start = dt.datetime.utcnow()

        t = 0.0
        while t < exptime_s:
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
            img = self.drv.start_readout(mode.mode, top, left, width, height)
        except Exception:
            self.log.exception("Error during readout")
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
