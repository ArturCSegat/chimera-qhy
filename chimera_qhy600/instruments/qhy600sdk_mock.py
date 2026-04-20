from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np

from qhy600sdk import ControlId, QhyChipInfo, StreamMode


@dataclass
class _MockCamera:
    camera_id: bytes
    stream_mode: StreamMode = StreamMode.SINGLE_FRAME
    readout_mode_index: int = 1

    bits_per_pixel: int = 16
    bin_x: int = 1
    bin_y: int = 1
    roi_left: int = 0
    roi_top: int = 0
    roi_width: int = 9600
    roi_height: int = 6422

    params: Dict[ControlId, float] = field(default_factory=dict)

    last_frame: np.ndarray | None = None


class QhyCcdSdkMock:
    """Mock implementation of QhyCcdSdk for local testing.

    Behavior:
    - Every method prints when called.
    - Only image-affecting operations (binning, ROI, exposure/read) update state and
      generate the synthetic image.

    This is a drop-in replacement for the driver layer.
    """

    def __init__(self, *, image_width: int = 9600, image_height: int = 6422):
        self._full_w = int(image_width)
        self._full_h = int(image_height)
        self._initialized = False
        self._next_handle = 1
        self._cams: Dict[int, _MockCamera] = {}

        print(f"[QhyCcdSdkMock] init (sensor={self._full_w}x{self._full_h})")

    def initialize_sdk(self) -> None:
        print("[QhyCcdSdkMock] initialize_sdk")
        self._initialized = True

    def shutdown_sdk(self) -> None:
        print("[QhyCcdSdkMock] shutdown_sdk")
        self._initialized = False
        self._cams.clear()

    def scan_cameras(self) -> int:
        print("[QhyCcdSdkMock] scan_cameras")
        return 1

    def get_camera_id(self, index: int = 0) -> bytes:
        print(f"[QhyCcdSdkMock] get_camera_id(index={index})")
        return b"QHY600M-MOCK"

    def open_camera(self, camera_id: bytes) -> int:
        print(f"[QhyCcdSdkMock] open_camera(camera_id={camera_id!r})")
        if not self._initialized:
            raise RuntimeError("SDK not initialized")

        handle = self._next_handle
        self._next_handle += 1

        cam = _MockCamera(camera_id=camera_id)
        cam.roi_width = self._full_w
        cam.roi_height = self._full_h
        cam.params[ControlId.GAIN] = 10.0
        cam.params[ControlId.EXPOSURE_US] = 1_000_000.0
        cam.params[ControlId.TEMPERATURE_C] = -10.0

        self._cams[handle] = cam
        return handle

    def close_camera(self, handle: int) -> None:
        print(f"[QhyCcdSdkMock] close_camera(handle={handle})")
        self._cams.pop(int(handle), None)

    def set_stream_mode(self, handle: int, mode: StreamMode) -> None:
        print(f"[QhyCcdSdkMock] set_stream_mode(handle={handle}, mode={mode})")
        self._cams[int(handle)].stream_mode = mode

    def initialize_camera(self, handle: int) -> None:
        print(f"[QhyCcdSdkMock] initialize_camera(handle={handle})")

    def get_readout_modes_count(self, handle: int) -> int:
        print(f"[QhyCcdSdkMock] get_readout_modes_count(handle={handle})")
        return 3

    def get_readout_mode_name(self, handle: int, index: int) -> str:
        print(f"[QhyCcdSdkMock] get_readout_mode_name(handle={handle}, index={index})")
        names = {
            0: "Photographic",
            1: "High Gain",
            2: "Extended Fullwell",
        }
        return names.get(int(index), f"Mode{index}")

    def get_readout_mode_resolution(self, handle: int, index: int) -> tuple[int, int]:
        print(f"[QhyCcdSdkMock] get_readout_mode_resolution(handle={handle}, index={index})")
        return self._full_w, self._full_h

    def set_readout_mode(self, handle: int, index: int) -> None:
        print(f"[QhyCcdSdkMock] set_readout_mode(handle={handle}, index={index})")
        self._cams[int(handle)].readout_mode_index = int(index)

    def get_chip_info(self, handle: int) -> QhyChipInfo:
        print(f"[QhyCcdSdkMock] get_chip_info(handle={handle})")
        cam = self._cams[int(handle)]
        return QhyChipInfo(
            chip_width_mm=36.0,
            chip_height_mm=24.0,
            image_width_px=self._full_w,
            image_height_px=self._full_h,
            pixel_width_um=3.76,
            pixel_height_um=3.76,
            bits_per_pixel=int(cam.bits_per_pixel),
        )

    def set_bits_per_pixel(self, handle: int, bits: int) -> None:
        print(f"[QhyCcdSdkMock] set_bits_per_pixel(handle={handle}, bits={bits})")
        self._cams[int(handle)].bits_per_pixel = int(bits)

    def set_parameter(self, handle: int, control_id: ControlId, value: float) -> None:
        print(f"[QhyCcdSdkMock] set_parameter(handle={handle}, control_id={control_id}, value={value})")
        self._cams[int(handle)].params[control_id] = float(value)

    def get_parameter(self, handle: int, control_id: ControlId) -> float:
        print(f"[QhyCcdSdkMock] get_parameter(handle={handle}, control_id={control_id})")
        return float(self._cams[int(handle)].params.get(control_id, 0.0))

    def set_binning(self, handle: int, bin_x: int, bin_y: int) -> None:
        print(f"[QhyCcdSdkMock] set_binning(handle={handle}, bin_x={bin_x}, bin_y={bin_y})")
        cam = self._cams[int(handle)]
        cam.bin_x = max(1, int(bin_x))
        cam.bin_y = max(1, int(bin_y))

    def set_roi(self, handle: int, left: int, top: int, width: int, height: int) -> None:
        print(
            f"[QhyCcdSdkMock] set_roi(handle={handle}, left={left}, top={top}, width={width}, height={height})"
        )
        cam = self._cams[int(handle)]
        cam.roi_left = max(0, int(left))
        cam.roi_top = max(0, int(top))
        cam.roi_width = max(1, int(width))
        cam.roi_height = max(1, int(height))

    def start_single_frame_exposure(self, handle: int) -> None:
        print(f"[QhyCcdSdkMock] start_single_frame_exposure(handle={handle})")
        cam = self._cams[int(handle)]

        w = cam.roi_width
        h = cam.roi_height
        bpp = cam.bits_per_pixel

        gain = float(cam.params.get(ControlId.GAIN, 10.0))
        exptime_us = float(cam.params.get(ControlId.EXPOSURE_US, 1_000_000.0))

        seed = int(exptime_us) ^ int(gain * 100) ^ (w << 8) ^ (h << 1)
        rng = np.random.default_rng(seed)

        scale = max(0.1, min(50.0, (exptime_us / 1_000_000.0) * (gain / 10.0)))
        base = np.linspace(0, 1.0, h, dtype=np.float32)[:, None]
        img_f = (base * 1000.0 + rng.normal(0.0, 10.0, size=(h, w)).astype(np.float32)) * scale

        #apply binning
        if cam.bin_x > 1 or cam.bin_y > 1:
            img_f = img_f.reshape(
                (h // cam.bin_y, cam.bin_y, w // cam.bin_x, cam.bin_x)
            ).sum(axis=(1, 3))



        if bpp == 16:
            cam.last_frame = np.clip(img_f, 0, 65535).astype(np.uint16)
        else:
            cam.last_frame = np.clip(img_f / 256.0, 0, 255).astype(np.uint8)

    def read_single_frame(self, handle: int, buffer_len: int) -> tuple[int, int, int, int, bytearray]:
        print(f"[QhyCcdSdkMock] read_single_frame(handle={handle}, buffer_len={buffer_len})")
        cam = self._cams[int(handle)]
        if cam.last_frame is None:
            # If caller forgot to expose, create one.
            self.start_single_frame_exposure(handle)

        frame = cam.last_frame
        h, w = frame.shape
        bpp = 16 if frame.dtype == np.uint16 else 8
        channels = 1

        needed = int(w * h * (bpp // 8))
        if int(buffer_len) < needed:
            raise RuntimeError(f"Buffer too small: buffer_len={buffer_len}, needed={needed}")

        out = bytearray(int(buffer_len))
        out[:needed] = frame.tobytes(order="C")

        return w, h, bpp, channels, out
