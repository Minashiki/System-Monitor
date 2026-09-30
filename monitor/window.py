"""Main window: live readings and rolling usage curves."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from monitor.sampler import Sample, Sampler
from monitor.session import Session

pg.setConfigOptions(antialias=True, background="#1b1b1b", foreground="#dddddd")

HISTORY = 120
INTERVAL_MS = 1000
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1b1b1b;
    color: #e6e6e6;
}
QFrame#topBar {
    background-color: #262626;
    border-radius: 6px;
}
QLabel#metric {
    font-size: 14px;
    padding: 2px 10px;
}
QLabel#status {
    color: #b0b0b0;
    font-size: 12px;
}
QLabel#cpuCore {
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 12px;
}
QPushButton#logButton {
    background-color: #2e7d32;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 18px;
    font-size: 14px;
}
QPushButton#logButton:hover {
    background-color: #388e3c;
}
"""

_RECORDING_BUTTON = """
QPushButton#logButton {
    background-color: #c62828;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 18px;
    font-size: 14px;
}
QPushButton#logButton:hover {
    background-color: #d32f2f;
}
"""


def _apply_cjk_font() -> None:
    app = QApplication.instance()
    if app is None:
        return
    families = set(QFontDatabase.families())
    for name in ("Noto Sans CJK SC", "Noto Sans CJK JP", "Noto Sans SC", "WenQuanYi Micro Hei"):
        if name in families:
            app.setFont(QFont(name, 10))
            return


def _gb(num_bytes: int) -> str:
    return f"{num_bytes / (1024 ** 3):.1f}"


def _push(history: list[float], value: float) -> None:
    history.append(value)
    if len(history) > HISTORY:
        del history[:-HISTORY]


def _xy(history: Sequence[float]) -> tuple[list[int], list[float]]:
    if len(history) >= HISTORY:
        values = list(history[-HISTORY:])
    else:
        values = [float("nan")] * (HISTORY - len(history)) + list(history)
    xs = list(range(-(HISTORY - 1), 1))
    return xs, values


def _make_plot(title: str, unit: str = "%", y_max: float = 100) -> pg.PlotWidget:
    plot = pg.PlotWidget()
    plot.setTitle(title)
    plot.setLabel("bottom", "秒")
    plot.setLabel("left", unit)
    plot.showGrid(x=True, y=True, alpha=0.25)
    plot.setYRange(0, y_max, padding=0)
    plot.setXRange(-(HISTORY - 1), 0, padding=0)
    plot.setMouseEnabled(x=False, y=False)
    plot.hideButtons()
    plot.setMenuEnabled(False)
    return plot


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        _apply_cjk_font()
        self.setWindowTitle("资源监视器")
        self.resize(1400, 860)
        self.setMinimumSize(1180, 720)
        self.setStyleSheet(_STYLESHEET)

        self.sampler = Sampler()
        self.session: Session | None = None
        self.cpu_total_hist: list[float] = []
        self.cpu_per_hist: list[list[float]] = [[] for _ in range(self.sampler.cpu_count)]
        self.memory_hist: list[float] = []
        self.swap_hist: list[float] = []
        self.gpu_hist: list[float] = []
        self.vram_hist: list[float] = []
        self.gpu_temp_hist: list[float] = []

        self._build_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(INTERVAL_MS)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        bar = QFrame()
        bar.setObjectName("topBar")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 8, 8, 8)
        self.cpu_label = self._metric_label("CPU  --")
        self.mem_label = self._metric_label("内存  --")
        self.swap_label = self._metric_label("交换  --")
        self.gpu_label = self._metric_label("GPU  --")
        self.vram_label = self._metric_label("显存  --")
        self.gpu_temp_label = self._metric_label("GPU温度  --")
        for label in (
            self.cpu_label,
            self.mem_label,
            self.swap_label,
            self.gpu_label,
            self.vram_label,
            self.gpu_temp_label,
        ):
            bar_layout.addWidget(label)
        bar_layout.addStretch(1)
        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        bar_layout.addWidget(self.status_label)
        self.log_button = QPushButton("开始记录")
        self.log_button.setObjectName("logButton")
        self.log_button.setMinimumWidth(120)
        self.log_button.clicked.connect(self._toggle_log)
        bar_layout.addWidget(self.log_button)
        root.addWidget(bar)

        self.cpu_plot = _make_plot("CPU 总体")
        self.cpu_total_curve = self.cpu_plot.plot(pen=pg.mkPen("#4fc3f7", width=2))
        root.addWidget(self.cpu_plot, stretch=2)

        cpu_row = QHBoxLayout()
        self.per_plot = _make_plot("各逻辑处理器")
        self.cpu_curves = []
        self.cpu_labels: list[QLabel] = []
        count = self.sampler.cpu_count
        for index in range(count):
            color = pg.hsvColor(index / max(count, 1), 0.8, 1.0)
            curve = self.per_plot.plot(pen=pg.mkPen(color, width=1.4))
            self.cpu_curves.append(curve)
            label = QLabel(f"CPU{index:<2d}   --")
            label.setObjectName("cpuCore")
            label.setStyleSheet(f"color: {color.name()};")
            self.cpu_labels.append(label)
        cpu_row.addWidget(self.per_plot, stretch=1)

        side = QWidget()
        grid = QGridLayout(side)
        grid.setContentsMargins(8, 20, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(2)
        rows = (count + 1) // 2
        for index, label in enumerate(self.cpu_labels):
            grid.addWidget(label, index % rows, index // rows)
        side.setFixedWidth(250)
        cpu_row.addWidget(side)
        root.addLayout(cpu_row, stretch=3)

        bottom = QHBoxLayout()
        self.mem_plot = _make_plot("内存")
        self.swap_plot = _make_plot("交换分区")
        self.gpu_plot = _make_plot("GPU 占用")
        self.vram_plot = _make_plot("显存")
        self.gpu_temp_plot = _make_plot("GPU 核心温度", unit="°C", y_max=110)
        self.mem_curve = self.mem_plot.plot(pen=pg.mkPen("#81c784", width=2))
        self.swap_curve = self.swap_plot.plot(pen=pg.mkPen("#ffb74d", width=2))
        self.gpu_curve = self.gpu_plot.plot(pen=pg.mkPen("#ce93d8", width=2))
        self.vram_curve = self.vram_plot.plot(pen=pg.mkPen("#f48fb1", width=2))
        self.gpu_temp_curve = self.gpu_temp_plot.plot(pen=pg.mkPen("#ff7043", width=2))
        for plot in (
            self.mem_plot,
            self.swap_plot,
            self.gpu_plot,
            self.vram_plot,
            self.gpu_temp_plot,
        ):
            bottom.addWidget(plot, stretch=1)
        root.addLayout(bottom, stretch=2)

    def _metric_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("metric")
        return label

    def _tick(self) -> None:
        try:
            sample = self.sampler.read()
        except Exception as exc:
            self.status_label.setText(f"采样失败: {exc}")
            return
        self._update_labels(sample)
        self._update_plots(sample)
        if self.session is not None and self.session.active:
            try:
                self.session.add(sample)
            except OSError as exc:
                self.status_label.setText(f"写入日志失败: {exc}")

    def _update_labels(self, sample: Sample) -> None:
        self.cpu_label.setText(f"CPU  {sample.cpu_total:.1f}%")
        self.mem_label.setText(
            f"内存  {_gb(sample.memory_used)} / {_gb(sample.memory_total)} GB"
            f" ({sample.memory_percent:.1f}%)"
        )
        self.swap_label.setText(
            f"交换  {_gb(sample.swap_used)} / {_gb(sample.swap_total)} GB"
            f" ({sample.swap_percent:.1f}%)"
        )
        if sample.gpu is None:
            self.gpu_label.setText("GPU  不可用")
            self.vram_label.setText("显存  不可用")
            self.gpu_temp_label.setText("GPU温度  不可用")
            self.gpu_plot.setTitle("GPU 占用（不可用）")
            self.vram_plot.setTitle("显存（不可用）")
            self.gpu_temp_plot.setTitle("GPU 核心温度（不可用）")
        else:
            self.gpu_label.setText(f"GPU  {sample.gpu.util:.1f}%")
            self.vram_label.setText(
                f"显存  {sample.gpu.vram_used_mib:.0f} / {sample.gpu.vram_total_mib:.0f} MiB"
                f" ({sample.gpu.vram_percent:.1f}%)"
            )
            if sample.gpu.temp_c is None:
                self.gpu_temp_label.setText("GPU温度  --")
            else:
                self.gpu_temp_label.setText(f"GPU温度  {sample.gpu.temp_c:.0f}°C")
            self.gpu_plot.setTitle("GPU 占用")
            self.vram_plot.setTitle("显存")
            self.gpu_temp_plot.setTitle("GPU 核心温度")
        for index, value in enumerate(sample.cpu_per):
            if index < len(self.cpu_labels):
                self.cpu_labels[index].setText(f"CPU{index:<2d} {value:5.1f}%")

    def _update_plots(self, sample: Sample) -> None:
        _push(self.cpu_total_hist, sample.cpu_total)
        self.cpu_total_curve.setData(*_xy(self.cpu_total_hist))
        for index, value in enumerate(sample.cpu_per):
            if index >= len(self.cpu_per_hist):
                break
            _push(self.cpu_per_hist[index], value)
            self.cpu_curves[index].setData(*_xy(self.cpu_per_hist[index]))
        _push(self.memory_hist, sample.memory_percent)
        _push(self.swap_hist, sample.swap_percent)
        gpu_util = float("nan") if sample.gpu is None else sample.gpu.util
        vram = float("nan") if sample.gpu is None else sample.gpu.vram_percent
        if sample.gpu is None or sample.gpu.temp_c is None:
            gpu_temp = float("nan")
        else:
            gpu_temp = sample.gpu.temp_c
        _push(self.gpu_hist, gpu_util)
        _push(self.vram_hist, vram)
        _push(self.gpu_temp_hist, gpu_temp)
        self.mem_curve.setData(*_xy(self.memory_hist))
        self.swap_curve.setData(*_xy(self.swap_hist))
        self.gpu_curve.setData(*_xy(self.gpu_hist))
        self.vram_curve.setData(*_xy(self.vram_hist))
        self.gpu_temp_curve.setData(*_xy(self.gpu_temp_hist))

    def _toggle_log(self) -> None:
        if self.session is not None and self.session.active:
            self.session.stop()
            self.log_button.setText("开始记录")
            self.log_button.setStyleSheet("")
            self.status_label.setText(f"已停止，已写入 {self.session.path.name}")
            return
        self.session = Session(LOG_DIR, self.sampler.cpu_count, interval_s=INTERVAL_MS / 1000)
        self.log_button.setText("停止记录")
        self.log_button.setStyleSheet(_RECORDING_BUTTON)
        self.status_label.setText(f"记录中 {self.session.path.name}")

    def closeEvent(self, event) -> None:
        if self.session is not None and self.session.active:
            self.session.stop()
        self.sampler.close()
        super().closeEvent(event)
