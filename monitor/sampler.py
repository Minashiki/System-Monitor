"""Non-blocking samples of CPU, memory, swap, and GPU."""

from __future__ import annotations

from dataclasses import dataclass

import psutil

from monitor.gpu import GpuReader, GpuSample


@dataclass(frozen=True)
class Sample:
    cpu_total: float
    cpu_per: tuple[float, ...]
    memory_percent: float
    memory_used: int
    memory_total: int
    swap_percent: float
    swap_used: int
    swap_total: int
    gpu: GpuSample | None


class Sampler:
    def __init__(self) -> None:
        self.gpu_reader = GpuReader()
        self.cpu_count = psutil.cpu_count(logical=True) or 1
        # Prime the counters so the next call returns a real delta.
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)

    def close(self) -> None:
        self.gpu_reader.close()

    def read(self) -> Sample:
        cpu_total = float(psutil.cpu_percent(interval=None))
        per = [float(value) for value in psutil.cpu_percent(interval=None, percpu=True)]
        if len(per) < self.cpu_count:
            per.extend([0.0] * (self.cpu_count - len(per)))
        elif len(per) > self.cpu_count:
            per = per[: self.cpu_count]

        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return Sample(
            cpu_total=cpu_total,
            cpu_per=tuple(per),
            memory_percent=float(memory.percent),
            memory_used=int(memory.used),
            memory_total=int(memory.total),
            swap_percent=float(swap.percent),
            swap_used=int(swap.used),
            swap_total=int(swap.total),
            gpu=self.gpu_reader.read(),
        )
