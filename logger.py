from __future__ import annotations

import os
import queue
import threading
from datetime import datetime

from calibration import Calibration
from config import DAQConfig


class DataLogger(threading.Thread):
    def __init__(
        self,
        config: DAQConfig,
        data_queue: queue.Queue,
        stop_event: threading.Event,
        output_dir: str,
        calibration: Calibration | None = None,
    ):
        super().__init__(daemon=True)
        self.config = config
        self.data_queue = data_queue
        self.stop_event = stop_event
        self.output_dir = output_dir
        self.calibration = calibration or Calibration()

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)
        filename = f"torque_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", newline="") as f:
            f.write(f"# Sample Rate: {self.config.sample_rate}\n")
            f.write(f"# Channel: {self.config.channel}\n")
            f.write(f"# Voltage Range: ±{self.config.voltage_range}V\n")
            f.write(f"# Calibration: {self.calibration.mode}\n")
            f.write(f"# Mode: {self.config.mode}\n")
            f.write(f"# Start Time: {datetime.now().isoformat()}\n")
            f.write("timestamp,elapsed_s,voltage_V,torque_Nm\n")

            while not self.stop_event.is_set():
                try:
                    sample = self.data_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                voltage = sample["voltage"]
                torque = self.calibration.convert(voltage)
                torque_str = f"{torque:.4f}" if torque is not None else ""
                f.write(
                    f"{sample['timestamp']},"
                    f"{sample['elapsed_s']:.6f},"
                    f"{voltage:.6f},"
                    f"{torque_str}\n"
                )
                f.flush()
