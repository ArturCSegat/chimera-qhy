from chimera.core.event import event
from chimera.core.lock import lock
from chimera.interfaces.camera import CCD, ReadoutMode, CameraStatus
from chimera.instruments.camera import CameraBase
import numpy as np
from qhy600mdriver import QHY600MDriver
import datetime as dt
import time

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
        self["device"] = 'USB'
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

        #TODO reference: https://www.qhyccd.com/astronomical-camera-qhy600/#:~:text=Readout%20Mode%20%230%20(Photographic%20Mode)
        readout_mode = ReadoutMode()
        readout_mode.mode = 0
        readout_mode.gain = 10
        readout_mode.width = 9600
        readout_mode.height = 6422
        readout_mode.pixel_width = 3.76
        readout_mode.pixel_height = 3.76
        self._readout_modes = {self._current_ccd: {self._current_readout_mode: readout_mode}}
        # TODO initialize the actual camera driver
        #self.drv = QHY600MDriver()
    
    def __start__(self):
        # TODO open the actual camera
        #self.drv.open()
        pass
    
    def is_cooling(self):
        return False #TODO
    
    def is_fanning(self):
        return False #TODO

    @lock
    def get_temperature(self):
        return 0.0 #TODO
    
    def supports(self, feature=None):
        return False #TODO
    
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
        return (0, 0) #TODO is it possible to set this value in the QHY600? Because it returned 0 x 0 in the SDK.
    
    def get_binnings(self):
        return self._binnings
    
    def get_readout_modes(self):
        return self._readout_modes

    def _expose(self, image_request):
        self.expose_begin(image_request)

        status = CameraStatus.OK
        
        #TODO start exposure on the actual camera
        # something like: self.drv.startExposure(self.ccd, int(imageRequest["exptime"] * 100), shutter)
        # Temporary to simulate exposure time:
        # +++++++++++++++++++++++++++++++++++++
        t = 0
        self._last_frame_start = dt.datetime.utcnow()
        while t < image_request["exptime"]:
            if self.abort.is_set():
                status = CameraStatus.ABORTED
                break

            time.sleep(0.1)
            t += 0.1
        # +++++++++++++++++++++++++++++++++++++

        self.expose_complete(image_request, status)

    def _readout(self, image_request):
        (mode, binning, top, left, width, height) = self._get_readout_mode_info(
            image_request["binning"], image_request["window"]
        )

        self.readout_begin(image_request)
        
        img = np.zeros((height, width), np.int32)
        #img = self.get_fake_image(width, height)

        #TODO read the image from the actual camera
        #
        # Something like: self.drv.startReadout(self.ccd, mode.mode, (top, left, width, height))
        #
        # If the readout fails: CameraStatus.ABORTED
        # If it works save the image and then: CameraStatus.OK
        
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
        with open('/home/vlm/tmp/imagem_via_SDK_byte-array.raw', 'rb') as raw_file:
            raw_data = raw_file.read()

        # Converte para array numpy
        image_array = np.frombuffer(raw_data, dtype=np.uint16)

        # Redimensiona para as dimensões do sensor
        try:
            img = image_array.reshape((height, width))
        except ValueError:
            # Tenta a orientação oposta se a primeira não funcionar
            print("Tentando orientação alternativa...")
            img = image_array.reshape((width, height)).T

        return img