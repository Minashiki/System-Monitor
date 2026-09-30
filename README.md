# 资源监视器 / Resource Monitor

Ubuntu 24 桌面资源监视器。每秒刷新 CPU、内存、交换分区、GPU 占用、显存和 GPU 核心温度，并画出最近 120 秒的曲线。

A desktop resource monitor for Ubuntu 24. It refreshes CPU, memory, swap, GPU utilization, VRAM, and GPU core temperature once a second, and plots the last 120 seconds.

## 运行环境 / Requirements

- Ubuntu 24，带图形界面 / Ubuntu 24 with a desktop session
- Anaconda base（`/home/minashiki/anaconda3/bin/python`，Python 3.14）
- NVIDIA 驱动可选。读不到显卡时，GPU、显存和核心温度显示「不可用」，其余项目照常刷新。
- An optional NVIDIA driver. If the GPU cannot be read, GPU, VRAM, and core temperature show as unavailable and the other charts keep updating.

## 安装 / Install

依赖装进 Anaconda base，不另建虚拟环境。

Install into the Anaconda base environment. Do not create a separate virtual environment.

```bash
/home/minashiki/anaconda3/bin/python -m pip install -r requirements.txt
```

## 启动 / Run

```bash
cd /home/minashiki/SystemMonitor
python main.py
```

启动时会在 `~/.local/share/applications/systemmonitor.desktop` 写入桌面项。Ubuntu 顶栏用窗口类名匹配这个文件，再显示其中的「资源监视器」。类名本身必须是 ASCII；若把中文写进类名，顶栏会按 Latin-1 显示成乱码。

On startup the app writes `~/.local/share/applications/systemmonitor.desktop`. Ubuntu's top bar matches the window class to that file and shows its name, 资源监视器. The class itself has to be ASCII; a Chinese class name is shown as mojibake.

## 界面 / What you see

- **CPU 总体 / CPU total**：整机占用。
- **各逻辑处理器 / Logical processors**：每个逻辑处理器一条曲线（本机为 CPU0–CPU15），右侧是当前百分比。
- **内存、交换分区、GPU 占用、显存 / Memory, swap, GPU, VRAM**：占用百分比曲线。顶栏同时显示内存和显存的已用/总量。
- **GPU 核心温度 / GPU core temperature**：NVML 读取的 GPU 核心温度（°C），纵轴 0–110。顶栏显示当前温度。读不到温度时曲线留空，顶栏显示 `--`。

## 日志 / Logging

**开始记录 / Start** 后，在 `logs/` 下新建一个文件，例如 `logs/20260926_011500.log`。记录过程中持续覆盖写入本次会话的最小值、最大值和平均值。再按一次变为 **停止记录 / Stop**。关闭窗口时如果仍在记录，会先写上结束时间再退出。

Press **开始记录** to create a file under `logs/`, such as `logs/20260926_011500.log`. While recording, the file is overwritten with the minimum, maximum, and average of the current session. Press again to stop. Closing the window while recording writes the end time first.

日志保留一位小数。占用类为百分比，`gpu_temp` 为摄氏度。没有 GPU 数据时，对应项为 `n/a`。

Values keep one decimal place. Usage fields are percentages, and `gpu_temp` is degrees Celsius. GPU fields are `n/a` when no GPU data is available.
