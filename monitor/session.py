"""Recording session that keeps min, max, and average in one log file."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from monitor.sampler import Sample


@dataclass
class _Stats:
    count: int = 0
    minimum: float | None = None
    maximum: float | None = None
    total: float = 0.0

    def add(self, value: float | None) -> None:
        if value is None:
            return
        self.count += 1
        self.total += value
        if self.minimum is None or value < self.minimum:
            self.minimum = value
        if self.maximum is None or value > self.maximum:
            self.maximum = value

    @property
    def average(self) -> float | None:
        if self.count == 0:
            return None
        return self.total / self.count


def _display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if ord(char) > 0x1100 else 1
    return width


def _pad(text: str, width: int, align: str = "left") -> str:
    gap = max(0, width - _display_width(text))
    if align == "right":
        return (" " * gap) + text
    return text + (" " * gap)


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}"


class Session:
    def __init__(self, log_dir: Path, cpu_count: int, interval_s: float = 1.0) -> None:
        self.interval_s = interval_s
        self.started = datetime.now()
        self.stopped: datetime | None = None
        self.samples = 0
        self.active = True
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = self.started.strftime("%Y%m%d_%H%M%S")
        path = log_dir / f"{stamp}.log"
        if path.exists():
            path = log_dir / f"{stamp}_{self.started.microsecond:06d}.log"
        self.path = path
        names = (
            ["cpu_total"]
            + [f"cpu_{index}" for index in range(cpu_count)]
            + ["memory", "swap", "gpu_util", "vram", "gpu_temp"]
        )
        self.stats = {name: _Stats() for name in names}
        self.write()

    def add(self, sample: Sample) -> None:
        if not self.active:
            return
        self.samples += 1
        self.stats["cpu_total"].add(sample.cpu_total)
        for index, value in enumerate(sample.cpu_per):
            key = f"cpu_{index}"
            if key in self.stats:
                self.stats[key].add(value)
        self.stats["memory"].add(sample.memory_percent)
        self.stats["swap"].add(sample.swap_percent)
        if sample.gpu is None:
            self.stats["gpu_util"].add(None)
            self.stats["vram"].add(None)
            self.stats["gpu_temp"].add(None)
        else:
            self.stats["gpu_util"].add(sample.gpu.util)
            self.stats["vram"].add(sample.gpu.vram_percent)
            self.stats["gpu_temp"].add(sample.gpu.temp_c)
        self.write()

    def stop(self) -> None:
        if not self.active:
            return
        self.active = False
        self.stopped = datetime.now()
        self.write()

    def write(self) -> None:
        lines = ["状态: 记录中" if self.active else "状态: 已停止"]
        lines.append(f"开始: {self.started.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.stopped is not None:
            lines.append(f"结束: {self.stopped.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"采样间隔: {self.interval_s:.1f} s")
        lines.append(f"采样次数: {self.samples}")
        lines.append("")
        lines.append(
            _pad("项目", 16)
            + _pad("最小", 10, "right")
            + _pad("最大", 10, "right")
            + _pad("平均", 10, "right")
        )
        for name, stats in self.stats.items():
            lines.append(
                _pad(name, 16)
                + _pad(_fmt(stats.minimum), 10, "right")
                + _pad(_fmt(stats.maximum), 10, "right")
                + _pad(_fmt(stats.average), 10, "right")
            )
        text = "\n".join(lines) + "\n"
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(self.path)
