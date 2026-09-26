"""NVIDIA GPU utilization and VRAM via NVML."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GpuSample:
    name: str
    util: float
    vram_percent: float
    vram_used_mib: float
    vram_total_mib: float


class GpuReader:
    """Reads the first NVIDIA GPU. Stays unavailable if NVML cannot start."""

    def __init__(self) -> None:
        self._nvml = None
        self._handle = None
        self.name = ""
        self.available = False
        self._init()

    def _init(self) -> None:
        try:
            import pynvml
        except ImportError:
            return
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            raw_name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(raw_name, bytes):
                raw_name = raw_name.decode("utf-8", errors="replace")
            self._nvml = pynvml
            self._handle = handle
            self.name = str(raw_name)
            self.available = True
        except Exception:
            self._shutdown()

    def _shutdown(self) -> None:
        nvml = self._nvml
        self._nvml = None
        self._handle = None
        self.available = False
        if nvml is not None:
            try:
                nvml.nvmlShutdown()
            except Exception:
                pass

    def close(self) -> None:
        self._shutdown()

    def read(self) -> GpuSample | None:
        if not self.available or self._nvml is None or self._handle is None:
            return None
        try:
            util = self._nvml.nvmlDeviceGetUtilizationRates(self._handle)
            mem = self._nvml.nvmlDeviceGetMemoryInfo(self._handle)
        except Exception:
            return None
        total = float(mem.total)
        used = float(mem.used)
        percent = (used / total * 100.0) if total else 0.0
        mib = 1024 * 1024
        return GpuSample(
            name=self.name,
            util=float(util.gpu),
            vram_percent=percent,
            vram_used_mib=used / mib,
            vram_total_mib=total / mib,
        )
