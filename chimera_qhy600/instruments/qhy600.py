from chimera.core.event import event
from chimera.core.lock import lock
from chimera.interfaces.camera import CCD
from chimera.instruments.camera import CameraBase

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
    
    def __start__(self):
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
        return (0, 0) #TODO é possível settar esse varlor na QHY600? Pois elea retornou 0 x 0 no SDK.
    
    def get_binnings(self):
        return self._binnings