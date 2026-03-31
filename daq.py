from __future__ import annotations

import math
import queue
import threading
import time
from collections import deque
from datetime import datetime, timezone

from config import DAQConfig


class DAQReader(threading.Thread):
    def __init__(
        self,
        config: DAQConfig,
        data_queue: queue.Queue,
        plot_buffer: deque,
        stop_event: threading.Event,
        error_event: threading.Event,
        demo_mode: bool = False,
    ):
        super().__init__(daemon=True)
        self.config = config
        self.data_queue = data_queue
        self.plot_buffer = plot_buffer
        self.stop_event = stop_event
        self.error_event = error_event
        self.demo_mode = demo_mode

    def run(self):
        if self.demo_mode:
            self._run_demo()
        else:
            self._run_hardware()

    def _run_demo(self):
        interval = 1.0 / self.config.sample_rate
        start_time = time.perf_counter()
        while not self.stop_event.is_set():
            now = time.perf_counter()
            elapsed = now - start_time
            voltage = 2.5 + 1.5 * math.sin(2 * math.pi * 1.0 * elapsed)
            sample = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "elapsed_s": round(elapsed, 6),
                "voltage": round(voltage, 6),
            }
            self.data_queue.put(sample)
            self.plot_buffer.append(sample)
            sleep_target = start_time + (elapsed // interval + 1) * interval
            sleep_time = sleep_target - time.perf_counter()
            if sleep_time > 0:
                self.stop_event.wait(timeout=sleep_time)

    def _run_hardware(self):
        try:
            import nidaqmx
            from nidaqmx.constants import TerminalConfiguration

            vr = self.config.voltage_range
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan(
                    self.config.channel,
                    min_val=-vr,
                    max_val=vr,
                    terminal_config=TerminalConfiguration.RSE,
                )
                task.timing.cfg_samp_clk_timing(
                    rate=self.config.sample_rate,
                )
                start_time = time.perf_counter()
                while not self.stop_event.is_set():
                    voltage = task.read()
                    elapsed = time.perf_counter() - start_time
                    sample = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "elapsed_s": round(elapsed, 6),
                        "voltage": round(voltage, 6),
                    }
                    self.data_queue.put(sample)
                    self.plot_buffer.append(sample)
        except Exception:
            self.error_event.set()
