from __future__ import annotations

import ctypes
import ctypes.util
import os
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class QhyCcdError(RuntimeError):
    def __init__(self, func: str, code: int):
        super().__init__(f"QHYCCD SDK call failed: {func} returned {code}")
        self.func = func
        self.code = code


class ControlId(IntEnum):
    """Subset of QHY CONTROL_ID values used by this plugin."""

    GAIN = 6
    EXPOSURE_US = 8
    TEMPERATURE_C = 14
    CURRENT_PWM = 15
    MANUAL_PWM = 16
    COOLER = 18


class StreamMode(IntEnum):
    SINGLE_FRAME = 0
    LIVE = 1


def _resolve_sdk_library_path(explicit_path: Optional[str] = None) -> str:
    if explicit_path:
        return explicit_path

    env_path = os.getenv("QHYCCD_SDK_PATH") or os.getenv("QHYCCD_LIB_PATH")
    if env_path:
        return env_path

    for p in ("/usr/local/lib/libqhyccd.so", "/usr/lib64/libqhyccd.so", "/usr/lib/libqhyccd.so"):
        if os.path.exists(p):
            return p

    found = ctypes.util.find_library("qhyccd")
    if found:
        return found

    return "/usr/local/lib/libqhyccd.so"


@dataclass(frozen=True)
class QhyChipInfo:
    chip_width_mm: float
    chip_height_mm: float
    image_width_px: int
    image_height_px: int
    pixel_width_um: float
    pixel_height_um: float
    bits_per_pixel: int


class QhyCcdSdk:
    """ctypes-only wrapper around libqhyccd.

    This layer must:
    - Only deal with ctypes, function signatures, and raw SDK calls.
    - Not store camera global state (camera handle, ROI, etc.).
    """

    def __init__(self, library_path: Optional[str] = None):
        lib_path = _resolve_sdk_library_path(library_path)
        self._lib = ctypes.CDLL(lib_path)
        self._configure_signatures()

    def _configure_signatures(self) -> None:
        self._lib.InitQHYCCDResource.restype = ctypes.c_int
        self._lib.ReleaseQHYCCDResource.restype = ctypes.c_int
        self._lib.ScanQHYCCD.restype = ctypes.c_int

        self._lib.GetQHYCCDId.restype = ctypes.c_int
        self._lib.GetQHYCCDId.argtypes = [ctypes.c_int, ctypes.c_char_p]

        self._lib.OpenQHYCCD.restype = ctypes.c_void_p
        self._lib.OpenQHYCCD.argtypes = [ctypes.c_char_p]

        self._lib.CloseQHYCCD.restype = ctypes.c_int
        self._lib.CloseQHYCCD.argtypes = [ctypes.c_void_p]

        self._lib.InitQHYCCD.restype = ctypes.c_int
        self._lib.InitQHYCCD.argtypes = [ctypes.c_void_p]

        self._lib.SetQHYCCDStreamMode.restype = ctypes.c_int
        self._lib.SetQHYCCDStreamMode.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

        self._lib.GetQHYCCDNumberOfReadModes.restype = ctypes.c_int
        self._lib.GetQHYCCDNumberOfReadModes.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]

        self._lib.GetQHYCCDReadModeName.restype = ctypes.c_int
        self._lib.GetQHYCCDReadModeName.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p]

        self._lib.GetQHYCCDReadModeResolution.restype = ctypes.c_int
        self._lib.GetQHYCCDReadModeResolution.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
        ]

        self._lib.SetQHYCCDReadMode.restype = ctypes.c_int
        self._lib.SetQHYCCDReadMode.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

        self._lib.GetQHYCCDChipInfo.restype = ctypes.c_int
        self._lib.GetQHYCCDChipInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_uint32),
        ]

        self._lib.GetQHYCCDParam.restype = ctypes.c_double
        self._lib.GetQHYCCDParam.argtypes = [ctypes.c_void_p, ctypes.c_int]

        self._lib.SetQHYCCDParam.restype = ctypes.c_int
        self._lib.SetQHYCCDParam.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_double]

        self._lib.SetQHYCCDBitsMode.restype = ctypes.c_int
        self._lib.SetQHYCCDBitsMode.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

        self._lib.SetQHYCCDBinMode.restype = ctypes.c_int
        self._lib.SetQHYCCDBinMode.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32]

        self._lib.SetQHYCCDResolution.restype = ctypes.c_int
        self._lib.SetQHYCCDResolution.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]

        self._lib.IsQHYCCDControlAvailable.restype = ctypes.c_uint32
        self._lib.IsQHYCCDControlAvailable.argtypes = [ctypes.c_void_p, ctypes.c_int]

        # The plugin currently uses single-frame mode.
        self._lib.ExpQHYCCDSingleFrame.restype = ctypes.c_int
        self._lib.ExpQHYCCDSingleFrame.argtypes = [ctypes.c_void_p]

        self._lib.GetQHYCCDSingleFrame.restype = ctypes.c_int
        self._lib.GetQHYCCDSingleFrame.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint8),
        ]

    @staticmethod
    def _check_success(code: int, func: str) -> None:
        if int(code) != 0:
            raise QhyCcdError(func, int(code))

    @staticmethod
    def _as_handle(handle: int) -> ctypes.c_void_p:
        return ctypes.c_void_p(int(handle))

    def initialize_sdk(self) -> None:
        self._check_success(self._lib.InitQHYCCDResource(), "InitQHYCCDResource")

    def shutdown_sdk(self) -> None:
        self._check_success(self._lib.ReleaseQHYCCDResource(), "ReleaseQHYCCDResource")

    def scan_cameras(self) -> int:
        return int(self._lib.ScanQHYCCD())

    def get_camera_id(self, index: int = 0) -> bytes:
        buf = ctypes.create_string_buffer(32)
        self._check_success(
            self._lib.GetQHYCCDId(int(index), ctypes.cast(buf, ctypes.c_char_p)),
            "GetQHYCCDId",
        )
        return bytes(buf.value)

    def open_camera(self, camera_id: bytes) -> int:
        handle = self._lib.OpenQHYCCD(camera_id)
        if not handle:
            raise QhyCcdError("OpenQHYCCD", -1)
        return int(handle)

    def close_camera(self, handle: int) -> None:
        self._check_success(self._lib.CloseQHYCCD(self._as_handle(handle)), "CloseQHYCCD")

    def set_stream_mode(self, handle: int, mode: StreamMode) -> None:
        if mode not in StreamMode:
            raise TypeError("mode must be a StreamMode")
        self._check_success(
            self._lib.SetQHYCCDStreamMode(self._as_handle(handle), ctypes.c_uint32(int(mode))),
            "SetQHYCCDStreamMode",
        )

    def initialize_camera(self, handle: int) -> None:
        self._check_success(self._lib.InitQHYCCD(self._as_handle(handle)), "InitQHYCCD")

    def get_readout_modes_count(self, handle: int) -> int:
        n = ctypes.c_uint32()
        self._check_success(
            self._lib.GetQHYCCDNumberOfReadModes(self._as_handle(handle), ctypes.byref(n)),
            "GetQHYCCDNumberOfReadModes",
        )
        return int(n.value)

    def get_readout_mode_name(self, handle: int, index: int) -> str:
        name = ctypes.create_string_buffer(40)
        self._check_success(
            self._lib.GetQHYCCDReadModeName(
                self._as_handle(handle),
                ctypes.c_uint32(int(index)),
                ctypes.cast(name, ctypes.c_char_p),
            ),
            "GetQHYCCDReadModeName",
        )
        return name.value.decode("utf-8", errors="replace")

    def get_readout_mode_resolution(self, handle: int, index: int) -> tuple[int, int]:
        w = ctypes.c_uint32()
        h = ctypes.c_uint32()
        self._check_success(
            self._lib.GetQHYCCDReadModeResolution(
                self._as_handle(handle),
                ctypes.c_uint32(int(index)),
                ctypes.byref(w),
                ctypes.byref(h),
            ),
            "GetQHYCCDReadModeResolution",
        )
        return int(w.value), int(h.value)

    def set_readout_mode(self, handle: int, index: int) -> None:
        self._check_success(
            self._lib.SetQHYCCDReadMode(self._as_handle(handle), ctypes.c_uint32(int(index))),
            "SetQHYCCDReadMode",
        )

    def get_chip_info(self, handle: int) -> QhyChipInfo:
        chip_w = ctypes.c_double()
        chip_h = ctypes.c_double()
        img_w = ctypes.c_uint32()
        img_h = ctypes.c_uint32()
        pixel_w = ctypes.c_double()
        pixel_h = ctypes.c_double()
        bpp = ctypes.c_uint32()

        self._check_success(
            self._lib.GetQHYCCDChipInfo(
                self._as_handle(handle),
                ctypes.byref(chip_w),
                ctypes.byref(chip_h),
                ctypes.byref(img_w),
                ctypes.byref(img_h),
                ctypes.byref(pixel_w),
                ctypes.byref(pixel_h),
                ctypes.byref(bpp),
            ),
            "GetQHYCCDChipInfo",
        )

        return QhyChipInfo(
            chip_width_mm=float(chip_w.value),
            chip_height_mm=float(chip_h.value),
            image_width_px=int(img_w.value),
            image_height_px=int(img_h.value),
            pixel_width_um=float(pixel_w.value),
            pixel_height_um=float(pixel_h.value),
            bits_per_pixel=int(bpp.value),
        )

    def set_bits_per_pixel(self, handle: int, bits: int) -> None:
        self._check_success(
            self._lib.SetQHYCCDBitsMode(self._as_handle(handle), ctypes.c_uint32(int(bits))),
            "SetQHYCCDBitsMode",
        )

    def set_parameter(self, handle: int, control_id: ControlId, value: float) -> None:
        if control_id not in ControlId:
            raise TypeError("control_id must be a ControlId")
        self._check_success(
            self._lib.SetQHYCCDParam(self._as_handle(handle), int(control_id), ctypes.c_double(float(value))),
            "SetQHYCCDParam",
        )

    def get_parameter(self, handle: int, control_id: ControlId) -> float:
        if control_id not in ControlId:
            raise TypeError("control_id must be a ControlId")
        return float(self._lib.GetQHYCCDParam(self._as_handle(handle), int(control_id)))

    def is_control_available(self, handle: int, control_id: ControlId) -> bool:
        if control_id not in ControlId:
            raise TypeError("control_id must be a ControlId")
        return int(self._lib.IsQHYCCDControlAvailable(self._as_handle(handle), int(control_id))) == 0

    def set_binning(self, handle: int, bin_x: int, bin_y: int) -> None:
        self._check_success(
            self._lib.SetQHYCCDBinMode(
                self._as_handle(handle),
                ctypes.c_uint32(int(bin_x)),
                ctypes.c_uint32(int(bin_y)),
            ),
            "SetQHYCCDBinMode",
        )

    def set_roi(self, handle: int, left: int, top: int, width: int, height: int) -> None:
        self._check_success(
            self._lib.SetQHYCCDResolution(
                self._as_handle(handle),
                ctypes.c_uint32(int(left)),
                ctypes.c_uint32(int(top)),
                ctypes.c_uint32(int(width)),
                ctypes.c_uint32(int(height)),
            ),
            "SetQHYCCDResolution",
        )

    def start_single_frame_exposure(self, handle: int) -> None:
        self._check_success(self._lib.ExpQHYCCDSingleFrame(self._as_handle(handle)), "ExpQHYCCDSingleFrame")

    def read_single_frame(self, handle: int, buffer_len: int) -> tuple[int, int, int, int, bytearray]:
        """Read one frame into a buffer of size buffer_len.

        Returns: (width, height, bits_per_pixel, channels, buffer)
        """

        w = ctypes.c_uint32()
        h = ctypes.c_uint32()
        bpp = ctypes.c_uint32()
        channels = ctypes.c_uint32()

        buf = bytearray(int(buffer_len))
        c_buf = (ctypes.c_uint8 * int(buffer_len)).from_buffer(buf)

        self._check_success(
            self._lib.GetQHYCCDSingleFrame(
                self._as_handle(handle),
                ctypes.byref(w),
                ctypes.byref(h),
                ctypes.byref(bpp),
                ctypes.byref(channels),
                c_buf,
            ),
            "GetQHYCCDSingleFrame",
        )

        return int(w.value), int(h.value), int(bpp.value), int(channels.value), buf
