import ctypes
import time

import numpy as np

class QHY600MDriver:

    def __init__(self):
        self.qhyccd = ctypes.CDLL('/usr/local/lib/libqhyccd.so')
        self.qhyccd.GetQHYCCDParam.restype = ctypes.c_double
        self.qhyccd.OpenQHYCCD.restype = ctypes.POINTER(ctypes.c_uint32)
        self.gain = ctypes.c_double(10)
        self.exposure_time = ctypes.c_double(1000000)
        self.bpp = ctypes.c_uint32(16)
        self.binX = ctypes.c_uint32(1)
        self.binY = ctypes.c_uint32(1)

    def open(self):
        result = self.qhyccd.InitQHYCCDResource()
        if result == 0:
            print("### Init SDK Ok")
        else:
            raise Exception('SDK not found')

        cameras_found = self.qhyccd.ScanQHYCCD()
        if cameras_found > 0:
            print("### Camera OK")
        else:
            raise Exception("camera not found")

        position_id = 0
        type_char_array_32 = ctypes.c_char * 32
        id_object = type_char_array_32()
        result = self.qhyccd.GetQHYCCDId(position_id, id_object)
        print(f"### GetQHYCCDId() - result: {result} | camera ID: {id_object}")

        self.camera_handle = self.qhyccd.OpenQHYCCD(id_object)

        self.qhyccd.SetQHYCCDStreamMode(self.camera_handle, ctypes.c_uint32(0))
        self.qhyccd.InitQHYCCD(self.camera_handle)

        chipWidthMM = ctypes.c_uint32(0)
        chipHeightMM = ctypes.c_uint32(0)
        self.maxImageSizeX = ctypes.c_uint32(0)
        self.maxImageSizeY = ctypes.c_uint32(0)
        pixelWidthUM = ctypes.c_uint32(0)
        pixelHeightUM = ctypes.c_uint32(0)
        bpp = ctypes.c_uint32(0)
        result = self.qhyccd.GetQHYCCDChipInfo(
            self.camera_handle, ctypes.byref(chipWidthMM), ctypes.byref(chipHeightMM), ctypes.byref(self.maxImageSizeX),
            ctypes.byref(self.maxImageSizeY), ctypes.byref(pixelWidthUM), ctypes.byref(pixelHeightUM),
            ctypes.byref(bpp),
        )
        print(f"### GetQHYCCDChipInfo() - result: {result} | Camera info: {[
            chipWidthMM.value, chipHeightMM.value, self.maxImageSizeX.value, self.maxImageSizeY.value,
            pixelWidthUM.value, pixelHeightUM.value, bpp.value
        ]}")
    
    def close(self):
        # TODO stop exposure is needed?!
        #self.qhyccd.CancelQHYCCDExposingAndReadout(self.camera_handle)
        result = self.qhyccd.CloseQHYCCD(self.camera_handle)
        print(f"### CloseQHYCCD() - result: {result}")
        result = self.qhyccd.ReleaseQHYCCDResource()
        print(f"### ReleaseQHYCCDResource() - result: {result}")
    
    def start_exposure(self, exptime):
        print(f"### start_exposure() - exptime: {exptime} s")
        self.exposure_time = ctypes.c_double(exptime * 1000000)  # convert seconds to microseconds
        self.qhyccd.SetQHYCCDBitsMode(self.camera_handle, self.bpp)

        self.qhyccd.SetQHYCCDParam.restype = ctypes.c_uint32
        self.qhyccd.SetQHYCCDParam.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_double]

        self.qhyccd.SetQHYCCDParam(self.camera_handle, ctypes.c_int(6), self.gain)
        result = self.qhyccd.SetQHYCCDParam(self.camera_handle, ctypes.c_int(8), self.exposure_time)
        print(f"### SetQHYCCDParam(CONTROL_EXPOSURE) - result: {result} | exptime: {self.exposure_time.value} us")
        self.qhyccd.SetQHYCCDResolution(self.camera_handle, ctypes.c_uint32(0), ctypes.c_uint32(0), self.maxImageSizeX, self.maxImageSizeY)
        self.qhyccd.SetQHYCCDBinMode(self.camera_handle, self.binX, self.binY)
        
        self.qhyccd.ExpQHYCCDSingleFrame(self.camera_handle)
        # TODO is chimera already waits simulating exposure time?!
        #time.sleep(1)
        print("### start_exposure END")


    def start_readout(self, mode, top, left, width, height):
        print("### start_readout INIT")
        # TODO ignoring mode for now: SetQHYCCDStreamMode could be used again?
        # TODO ignoring top and left for now
        w = ctypes.c_uint32()
        h = ctypes.c_uint32()
        b = ctypes.c_uint32()
        c = ctypes.c_uint32()
        length = (self.maxImageSizeX.value // self.binX.value) * (self.maxImageSizeY.value // self.binY.value) * (self.bpp.value // 8)
        image_data = (ctypes.c_ubyte * length)()

        self.qhyccd.GetQHYCCDSingleFrame.argtypes = [ctypes.c_void_p, 
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint8)]

        result = self.qhyccd.GetQHYCCDSingleFrame(
            self.camera_handle, ctypes.byref(w), ctypes.byref(h),
            ctypes.byref(b), ctypes.byref(c), image_data,
        )

        print(f"### GetQHYCCDSingleFrame() - result: {result} | w: {w.value} | h: {h.value} | b: {b.value} | c: {c.value}")

        img_size = w.value * h.value * c.value * (b.value // 8)
        img = np.ctypeslib.as_array(image_data, shape=(img_size,))
        img = img.view(np.uint16).reshape((h.value, w.value))

        print("### start_readout END")        
        return img

    def get_temperature(self):
        temp = self.qhyccd.GetQHYCCDParam(self.camera_handle, ctypes.c_int(14))
        print(f"### get_temperature() - temp: {temp} °C")
        return temp