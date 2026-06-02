from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from qhy600sdk import ControlId, QhyCcdSdk, QhyChipInfo, StreamMode
from qhy600sdk_mock import QhyCcdSdkMock


@dataclass
class Qhy600State:
    camera_id: Optional[bytes] = None
    camera_handle: Optional[int] = None
    chip_info: Optional[QhyChipInfo] = None

    readout_mode_index: int = 1
    gain: float = 10.0
    bits_per_pixel: int = 16

    bin_factor: int = 1
    roi_left: int = 0
    roi_top: int = 0
    roi_width: int = 0
    roi_height: int = 0


class QHY600MDriver:
    """Driver layer (no ctypes)."""

    def __init__(
        self,
        chimera_logger: logging.Logger,
        sdk_library_path: str | None = None,
        readout_mode_index: int = 1,
        gain: float = 10.0,
        *,
        use_mock_sdk: bool = False,
    ):
        self.log = chimera_logger
        self._sdk_library_path = sdk_library_path
        self._sdk: QhyCcdSdk | QhyCcdSdkMock
        self._use_mock_sdk = bool(use_mock_sdk)

        self.state = Qhy600State(readout_mode_index=int(readout_mode_index), gain=float(gain))

    def open(self) -> None:
        if self._use_mock_sdk:
            self._sdk = QhyCcdSdkMock(image_width=9600, image_height=6422)  # type: ignore[assignment]
        else:
            self._sdk = QhyCcdSdk(self._sdk_library_path)

        self._sdk.initialize_sdk()

        cameras_found = self._sdk.scan_cameras()
        if cameras_found <= 0:
            raise RuntimeError("No QHY cameras found")

        self.state.camera_id = self._sdk.get_camera_id(0)
        self.log.info("QHY camera id: %s", self.state.camera_id)

        self.state.camera_handle = self._sdk.open_camera(self.state.camera_id)

        mode_count = self._sdk.get_readout_modes_count(self.state.camera_handle)
        if not (0 <= self.state.readout_mode_index < mode_count):
            raise ValueError(
                f"Invalid readout_mode_index={self.state.readout_mode_index}; camera reports {mode_count} modes"
            )

        for idx in range(mode_count):
            name = self._sdk.get_readout_mode_name(self.state.camera_handle, idx)
            w, h = self._sdk.get_readout_mode_resolution(self.state.camera_handle, idx)
            self.log.info("Readout mode %d: %s (%dx%d)", idx, name, w, h)

        self._sdk.set_readout_mode(self.state.camera_handle, self.state.readout_mode_index)
        self._sdk.set_stream_mode(self.state.camera_handle, StreamMode.SINGLE_FRAME)

        self._sdk.initialize_camera(self.state.camera_handle)

        self.state.chip_info = self._sdk.get_chip_info(self.state.camera_handle)
        self.state.bits_per_pixel = int(self.state.chip_info.bits_per_pixel) or 16

        self.log.info(
            "Chip %.2fx%.2f mm, image %dx%d px, pixel %.3fx%.3f um, %d bpp",
            self.state.chip_info.chip_width_mm,
            self.state.chip_info.chip_height_mm,
            self.state.chip_info.image_width_px,
            self.state.chip_info.image_height_px,
            self.state.chip_info.pixel_width_um,
            self.state.chip_info.pixel_height_um,
            self.state.bits_per_pixel,
        )

        # Default ROI = full frame.
        self.state.roi_left = 0
        self.state.roi_top = 0
        self.state.roi_width = self.state.chip_info.image_width_px
        self.state.roi_height = self.state.chip_info.image_height_px

    def close(self) -> None:
        if not self._sdk:
            return

        try:
            if self.state.camera_handle:
                self._sdk.close_camera(self.state.camera_handle)
        finally:
            self._sdk.shutdown_sdk()
            self.state.camera_handle = None

    def start_exposure(
        self,
        exptime_s: float,
        *,
        bin_factor: int = 1,
        roi: tuple[int, int, int, int] | None = None,
    ) -> None:
        if not self._sdk or not self.state.camera_handle:
            raise RuntimeError("Camera not open")

        exptime_s = float(exptime_s)
        exposure_us = exptime_s * 1_000_000.0
        self.log.info("ROI RECEIVED")
        self.log.info(roi)

        self.state.bin_factor = max(1, int(bin_factor))

        if roi is not None:
            left, top, width, height = roi
            self.state.roi_left = max(0, int(left))
            self.state.roi_top = max(0, int(top))
            self.state.roi_width = max(1, int(width // self.state.bin_factor))
            self.state.roi_height = max(1, int(height // self.state.bin_factor))
        elif self.state.chip_info:
            self.state.roi_left = 0
            self.state.roi_top = 0

            self.state.roi_width = self.state.chip_info.image_width_px // self.state.bin_factor
            self.state.roi_height = self.state.chip_info.image_height_px // self.state.bin_factor

        self.log.info(
            "Starting exposure: %.3fs (bin=%dx%d, roi=%d,%d %dx%d)",
            exptime_s,
            self.state.bin_factor,
            self.state.bin_factor,
            self.state.roi_left,
            self.state.roi_top,
            self.state.roi_width,
            self.state.roi_height,
        )

        self._sdk.set_bits_per_pixel(self.state.camera_handle, self.state.bits_per_pixel)
        self._sdk.set_parameter(self.state.camera_handle, ControlId.GAIN, self.state.gain)
        self._sdk.set_parameter(self.state.camera_handle, ControlId.EXPOSURE_US, exposure_us)

        self._sdk.set_binning(self.state.camera_handle, self.state.bin_factor, self.state.bin_factor)
        self._sdk.set_roi(
            self.state.camera_handle,
            self.state.roi_left,
            self.state.roi_top,
            self.state.roi_width,
            self.state.roi_height,
        )

        self._sdk.start_single_frame_exposure(self.state.camera_handle)

    def start_readout(self, mode: int, top: int, left: int, width: int, height: int) -> np.ndarray:
        """Readout the last exposed frame."""

        if not self._sdk or not self.state.camera_handle:
            raise RuntimeError("Camera not open")

        req_left = max(0, int(left))
        req_top = max(0, int(top))
        req_w = max(1, int(width))
        req_h = max(1, int(height))

        if (
            req_left != self.state.roi_left
            or req_top != self.state.roi_top
            or req_w != self.state.roi_width
            or req_h != self.state.roi_height
        ):
            self.log.warning(
                "Requested window %d,%d %dx%d differs from configured ROI %d,%d %dx%d; "
                "ROI is applied at exposure time",
                req_left,
                req_top,
                req_w,
                req_h,
                self.state.roi_left,
                self.state.roi_top,
                self.state.roi_width,
                self.state.roi_height,
            )

        bytes_per_pixel = max(1, self.state.bits_per_pixel // 8)
        buffer_len = int(self.state.roi_width * self.state.roi_height * bytes_per_pixel)

        frame_w, frame_h, bpp, channels, buf = self._sdk.read_single_frame(self.state.camera_handle, buffer_len)

        if channels != 1:
            raise RuntimeError(f"Unexpected channel count {channels} (this plugin is for monochrome cameras)")

        dtype = np.uint16 if bpp == 16 else np.uint8
        needed_bytes = int(frame_w * frame_h * (bpp // 8))
        raw = memoryview(buf)[:needed_bytes]

        arr = np.frombuffer(raw, dtype=dtype)
        return arr.reshape((frame_h, frame_w))

    def get_temperature(self) -> float:
        if not self._sdk or not self.state.camera_handle:
            raise RuntimeError("Camera not open")
        return self._sdk.get_parameter(self.state.camera_handle, ControlId.TEMPERATURE_C)
