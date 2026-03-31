from __future__ import annotations

import csv
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Calibration:
    mode: str = "none"
    slope: float = 1.0
    offset: float = 0.0
    _voltages: list[float] = field(default_factory=list, repr=False)
    _torques: list[float] = field(default_factory=list, repr=False)

    def convert(self, voltage: float) -> float | None:
        if self.mode == "none":
            return None
        if self.mode == "linear":
            return self.slope * voltage + self.offset
        if self.mode == "file":
            return float(np.interp(voltage, self._voltages, self._torques))
        return None

    def convert_array(self, voltages: np.ndarray) -> np.ndarray | None:
        if self.mode == "none":
            return None
        if self.mode == "linear":
            return self.slope * voltages + self.offset
        if self.mode == "file":
            return np.interp(voltages, self._voltages, self._torques)
        return None

    @classmethod
    def from_range(
        cls,
        voltage_min: float,
        voltage_max: float,
        torque_min: float,
        torque_max: float,
    ) -> Calibration:
        slope = (torque_max - torque_min) / (voltage_max - voltage_min)
        offset = torque_min - slope * voltage_min
        return cls(mode="linear", slope=slope, offset=offset)

    @classmethod
    def from_file(cls, path: str) -> Calibration:
        voltages = []
        torques = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                voltages.append(float(row["voltage"]))
                torques.append(float(row["torque"]))
        order = np.argsort(voltages)
        voltages = np.array(voltages)[order].tolist()
        torques = np.array(torques)[order].tolist()
        return cls(mode="file", _voltages=voltages, _torques=torques)
