import ctypes
import time

import numpy

class QHY600MDriver:

    def __init__(self):
        self.qhyccd = ctypes.CDLL('/usr/local/lib/libqhyccd.so')
        self.qhyccd.GetQHYCCDParam.restype = ctypes.c_double
        self.qhyccd.OpenQHYCCD.restype = ctypes.POINTER(ctypes.c_uint32)
        self.gain = ctypes.c_int(6)
        self.exposure_time = ctypes.c_int(8)
        self.depth = ctypes.c_uint32(8)

    def open(self):
        result = self.qhyccd.InitQHYCCDResource()
        if result == 0:
            print("Init SDK Ok")
        else:
            raise Exception('SDK not found')

        cameras_found = self.qhyccd.ScanQHYCCD()
        if cameras_found > 0:
            print("Camera OK\n")
        else:
            raise Exception('camera not found')

        position_id = 0
        type_char_array_32 = ctypes.c_char * 32
        id_object = type_char_array_32()
        result = self.qhyccd.GetQHYCCDId(position_id, id_object)

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
        camera_info = self.qhyccd.GetQHYCCDChipInfo(
            self.camera_handle, ctypes.byref(chipWidthMM), ctypes.byref(chipHeightMM), ctypes.byref(self.maxImageSizeX),
            ctypes.byref(self.maxImageSizeY), ctypes.byref(pixelWidthUM), ctypes.byref(pixelHeightUM),
            ctypes.byref(bpp),
        )
        print([
            chipWidthMM.value, chipHeightMM.value, self.maxImageSizeX.value, self.maxImageSizeY.value,
            pixelWidthUM.value, pixelHeightUM.value, bpp.value
        ])
    
    def close(self):
        self.qhyccd.CancelQHYCCDExposingAndReadout(self.camera_handle)
        self.qhyccd.CloseQHYCCD(self.camera_handle)
        self.qhyccd.ReleaseQHYCCDResource()
    
    def start_exposure(self, image_request):

        self.qhyccd.SetQHYCCDBitsMode(self.camera_handle, self.depth)

        self.qhyccd.SetQHYCCDParam.restype = ctypes.c_uint32
        self.qhyccd.SetQHYCCDParam.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_double]

        self.qhyccd.SetQHYCCDParam(self.camera_handle, self.gain, ctypes.c_double(10))
        self.qhyccd.SetQHYCCDParam(self.camera_handle, self.EXPOSURE_TIME, ctypes.c_double(1000000))
        self.qhyccd.SetQHYCCDResolution(self.camera_handle, ctypes.c_uint32(0), ctypes.c_uint32(0), self.maxImageSizeX, self.maxImageSizeY)
        self.qhyccd.SetQHYCCDBinMode(self.camera_handle, ctypes.c_uint32(1), ctypes.c_uint32(1))
        
        self.qhyccd.ExpQHYCCDSingleFrame(self.camera_handle)

        time.sleep(1) # TODO is it obligatory or do we need to wait? Chimera already waits simulating exposure time


    def get_image_data(self):
        image_data = (ctypes.c_uint8 * self.maxImageSizeX.value * self.maxImageSizeY.value)()
        channels = ctypes.c_uint32(1)

        response = self.qhyccd.GetQHYCCDSingleFrame(
            self.camera_handle, ctypes.byref(self.maxImageSizeX), ctypes.byref(self.maxImageSizeY),
            ctypes.byref(self.depth), ctypes.byref(channels), image_data,
        )

        print('RESPONSE: %s' % response)
        bytes_data = bytearray(image_data)
        print(bytes_data[0], bytes_data[1])

        raw_array = numpy.array(bytes_data)
        mono_image = raw_array.reshape(self.maxImageSizeY.value, self.maxImageSizeX.value)
        
        return mono_image
