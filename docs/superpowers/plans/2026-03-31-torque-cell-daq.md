# Torque Cell DAQ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a threaded Python DAQ application with a Plotly Dash web dashboard for reading, logging, and visualizing analog torque signals from a DYJN-104 load cell via NI USB-6002.

**Architecture:** Single process, three threads (DAQ reader, CSV logger, Dash main thread). DAQ thread pushes samples to a `queue.Queue` (for lossless CSV logging) and a `collections.deque` (for live plot display). Dash callbacks poll the deque on an interval to update the rolling chart.

**Tech Stack:** Python 3.9+, nidaqmx, Dash/Plotly, pandas, numpy

---

## File Structure

```
20260331_TorqueCellNI/
├── app.py                  # Entry point — creates shared state, starts threads, launches Dash
├── config.py               # Default settings and constants
├── daq.py                  # DAQReader class — background thread for hardware reads
├── logger.py               # DataLogger class — background thread for CSV writing
├── calibration.py          # Calibration loading and voltage→torque conversion
├── layout.py               # Dash HTML layout (sidebar, plot, controls, table)
├── callbacks.py            # Dash callback registration (start/stop, plot update, export)
├── requirements.txt        # Python dependencies
├── tests/
│   ├── test_config.py
│   ├── test_calibration.py
│   ├── test_daq.py
│   ├── test_logger.py
│   └── test_callbacks.py
├── data/                   # Auto-created for CSV output
└── calibration_files/      # Optional user calibration CSVs
```

---

### Task 1: Project Skeleton and Config

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create requirements.txt**

```
nidaqmx>=0.9.0
dash>=2.14.0
plotly>=5.18.0
pandas>=2.0.0
numpy>=1.24.0
pytest>=7.0.0
```

- [ ] **Step 2: Create virtual environment and install**

Run:
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

- [ ] **Step 3: Write the config test**

```python
# tests/test_config.py
from config import DAQConfig


def test_default_config():
    cfg = DAQConfig()
    assert cfg.channel == "Dev1/ai0"
    assert cfg.sample_rate == 100.0
    assert cfg.voltage_range == 5.0
    assert cfg.buffer_size == 5000
    assert cfg.csv_dir == "data"


def test_config_validates_sample_rate_max():
    cfg = DAQConfig(sample_rate=60000)
    assert cfg.sample_rate == 50000.0


def test_config_validates_sample_rate_min():
    cfg = DAQConfig(sample_rate=0)
    assert cfg.sample_rate == 1.0


def test_config_voltage_range_options():
    for vr in [1.0, 2.0, 5.0, 10.0]:
        cfg = DAQConfig(voltage_range=vr)
        assert cfg.voltage_range == vr


def test_config_invalid_voltage_range_clamps():
    cfg = DAQConfig(voltage_range=7.0)
    assert cfg.voltage_range == 10.0  # rounds up to nearest valid
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 5: Write config.py**

```python
# config.py
from dataclasses import dataclass, field

VALID_VOLTAGE_RANGES = [1.0, 2.0, 5.0, 10.0]
MAX_SAMPLE_RATE = 50000.0
MIN_SAMPLE_RATE = 1.0
DEFAULT_SAMPLE_RATE = 100.0
DEFAULT_CHANNEL = "Dev1/ai0"
DEFAULT_VOLTAGE_RANGE = 5.0
DEFAULT_BUFFER_SIZE = 5000
DEFAULT_CSV_DIR = "data"
AVAILABLE_CHANNELS = [f"Dev1/ai{i}" for i in range(8)]
PLOT_UPDATE_INTERVAL_MS = 250


@dataclass
class DAQConfig:
    channel: str = DEFAULT_CHANNEL
    sample_rate: float = DEFAULT_SAMPLE_RATE
    voltage_range: float = DEFAULT_VOLTAGE_RANGE
    buffer_size: int = DEFAULT_BUFFER_SIZE
    csv_dir: str = DEFAULT_CSV_DIR
    mode: str = "continuous"  # "one_shot", "timed", "continuous"
    timed_duration_s: float = 10.0

    def __post_init__(self):
        self.sample_rate = max(MIN_SAMPLE_RATE, min(self.sample_rate, MAX_SAMPLE_RATE))
        if self.voltage_range not in VALID_VOLTAGE_RANGES:
            self.voltage_range = min(
                VALID_VOLTAGE_RANGES, key=lambda v: v if v >= self.voltage_range else float("inf")
            )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt config.py tests/test_config.py
git commit -m "feat: add project skeleton with DAQConfig and defaults"
```

---

### Task 2: Calibration Module

**Files:**
- Create: `calibration.py`
- Create: `tests/test_calibration.py`

- [ ] **Step 1: Write the calibration tests**

```python
# tests/test_calibration.py
import os
import tempfile
import numpy as np
from calibration import Calibration


def test_no_calibration_returns_none():
    cal = Calibration()
    assert cal.convert(2.5) is None


def test_linear_calibration():
    cal = Calibration(mode="linear", slope=10.0, offset=0.0)
    assert cal.convert(2.5) == 25.0
    assert cal.convert(0.0) == 0.0
    assert cal.convert(5.0) == 50.0


def test_linear_calibration_with_offset():
    cal = Calibration(mode="linear", slope=10.0, offset=-5.0)
    assert cal.convert(2.5) == 20.0


def test_linear_from_range():
    cal = Calibration.from_range(
        voltage_min=0.0, voltage_max=5.0,
        torque_min=0.0, torque_max=100.0,
    )
    assert cal.convert(2.5) == 50.0
    assert cal.convert(0.0) == 0.0
    assert cal.convert(5.0) == 100.0


def test_file_calibration():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("voltage,torque\n")
        f.write("0.0,0.0\n")
        f.write("2.5,50.0\n")
        f.write("5.0,100.0\n")
        path = f.name
    try:
        cal = Calibration.from_file(path)
        assert cal.convert(1.25) == 25.0
        assert cal.convert(0.0) == 0.0
        assert cal.convert(5.0) == 100.0
    finally:
        os.unlink(path)


def test_convert_array():
    cal = Calibration(mode="linear", slope=10.0, offset=0.0)
    voltages = np.array([0.0, 1.0, 2.0, 3.0])
    result = cal.convert_array(voltages)
    np.testing.assert_array_equal(result, np.array([0.0, 10.0, 20.0, 30.0]))


def test_convert_array_no_calibration():
    cal = Calibration()
    voltages = np.array([1.0, 2.0])
    assert cal.convert_array(voltages) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_calibration.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'calibration'`

- [ ] **Step 3: Write calibration.py**

```python
# calibration.py
from __future__ import annotations

import csv
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Calibration:
    mode: str = "none"  # "none", "linear", "file"
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_calibration.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add calibration.py tests/test_calibration.py
git commit -m "feat: add calibration module with linear and file-based conversion"
```

---

### Task 3: DAQ Reader Thread

**Files:**
- Create: `daq.py`
- Create: `tests/test_daq.py`

- [ ] **Step 1: Write the DAQ reader tests (using demo/simulated mode)**

```python
# tests/test_daq.py
import queue
import threading
import time
from collections import deque

from daq import DAQReader
from config import DAQConfig


def test_daq_reader_demo_mode_produces_samples():
    q = queue.Queue()
    buf = deque(maxlen=100)
    stop_event = threading.Event()
    error_event = threading.Event()
    cfg = DAQConfig(sample_rate=100)

    reader = DAQReader(
        config=cfg,
        data_queue=q,
        plot_buffer=buf,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=True,
    )
    reader.start()
    time.sleep(0.3)
    stop_event.set()
    reader.join(timeout=2.0)

    assert not reader.is_alive()
    assert q.qsize() > 0
    assert len(buf) > 0


def test_daq_reader_sample_format():
    q = queue.Queue()
    buf = deque(maxlen=100)
    stop_event = threading.Event()
    error_event = threading.Event()
    cfg = DAQConfig(sample_rate=50)

    reader = DAQReader(
        config=cfg,
        data_queue=q,
        plot_buffer=buf,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=True,
    )
    reader.start()
    time.sleep(0.2)
    stop_event.set()
    reader.join(timeout=2.0)

    sample = q.get_nowait()
    assert "timestamp" in sample
    assert "elapsed_s" in sample
    assert "voltage" in sample


def test_daq_reader_stop_event_stops_thread():
    q = queue.Queue()
    buf = deque(maxlen=100)
    stop_event = threading.Event()
    error_event = threading.Event()
    cfg = DAQConfig(sample_rate=100)

    reader = DAQReader(
        config=cfg,
        data_queue=q,
        plot_buffer=buf,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=True,
    )
    reader.start()
    time.sleep(0.1)
    stop_event.set()
    reader.join(timeout=2.0)
    assert not reader.is_alive()


def test_daq_reader_error_event_on_failure():
    q = queue.Queue()
    buf = deque(maxlen=100)
    stop_event = threading.Event()
    error_event = threading.Event()
    cfg = DAQConfig(sample_rate=100, channel="FakeDevice/ai99")

    reader = DAQReader(
        config=cfg,
        data_queue=q,
        plot_buffer=buf,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=False,  # real mode, but device won't exist
    )
    reader.start()
    reader.join(timeout=3.0)
    assert error_event.is_set()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_daq.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'daq'`

- [ ] **Step 3: Write daq.py**

```python
# daq.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_daq.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add daq.py tests/test_daq.py
git commit -m "feat: add DAQReader thread with demo and hardware modes"
```

---

### Task 4: Data Logger Thread

**Files:**
- Create: `logger.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: Write the logger tests**

```python
# tests/test_logger.py
import os
import queue
import tempfile
import threading
import time

from logger import DataLogger
from config import DAQConfig


def test_logger_writes_csv_with_header():
    q = queue.Queue()
    stop_event = threading.Event()
    cfg = DAQConfig(sample_rate=100, channel="Dev1/ai0", voltage_range=5.0)

    with tempfile.TemporaryDirectory() as tmpdir:
        logger = DataLogger(
            config=cfg,
            data_queue=q,
            stop_event=stop_event,
            output_dir=tmpdir,
        )
        q.put({"timestamp": "2026-03-31T13:00:00", "elapsed_s": 0.0, "voltage": 2.5})
        q.put({"timestamp": "2026-03-31T13:00:00.01", "elapsed_s": 0.01, "voltage": 2.6})
        logger.start()
        time.sleep(0.3)
        stop_event.set()
        logger.join(timeout=2.0)

        files = os.listdir(tmpdir)
        assert len(files) == 1
        assert files[0].startswith("torque_log_")
        assert files[0].endswith(".csv")

        with open(os.path.join(tmpdir, files[0])) as f:
            content = f.read()
        assert "# Sample Rate: 100" in content
        assert "# Channel: Dev1/ai0" in content
        assert "timestamp,elapsed_s,voltage_V,torque_Nm" in content
        assert "2.5" in content
        assert "2.6" in content


def test_logger_creates_output_dir():
    q = queue.Queue()
    stop_event = threading.Event()
    cfg = DAQConfig()

    with tempfile.TemporaryDirectory() as tmpdir:
        nested = os.path.join(tmpdir, "subdir", "data")
        logger = DataLogger(
            config=cfg,
            data_queue=q,
            stop_event=stop_event,
            output_dir=nested,
        )
        stop_event.set()
        logger.start()
        logger.join(timeout=2.0)
        assert os.path.isdir(nested)


def test_logger_includes_torque_when_calibrated():
    q = queue.Queue()
    stop_event = threading.Event()
    cfg = DAQConfig()

    with tempfile.TemporaryDirectory() as tmpdir:
        from calibration import Calibration
        cal = Calibration(mode="linear", slope=10.0, offset=0.0)
        logger = DataLogger(
            config=cfg,
            data_queue=q,
            stop_event=stop_event,
            output_dir=tmpdir,
            calibration=cal,
        )
        q.put({"timestamp": "2026-03-31T13:00:00", "elapsed_s": 0.0, "voltage": 2.5})
        logger.start()
        time.sleep(0.3)
        stop_event.set()
        logger.join(timeout=2.0)

        files = os.listdir(tmpdir)
        with open(os.path.join(tmpdir, files[0])) as f:
            content = f.read()
        assert "25.0" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_logger.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'logger'`

- [ ] **Step 3: Write logger.py**

```python
# logger.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_logger.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add logger.py tests/test_logger.py
git commit -m "feat: add DataLogger thread with CSV output and calibration support"
```

---

### Task 5: Dash Layout

**Files:**
- Create: `layout.py`

- [ ] **Step 1: Write layout.py**

```python
# layout.py
from dash import dcc, html

from config import AVAILABLE_CHANNELS, DEFAULT_CHANNEL, DEFAULT_SAMPLE_RATE, VALID_VOLTAGE_RANGES


def create_layout() -> html.Div:
    return html.Div(
        style={"display": "flex", "fontFamily": "Arial, sans-serif", "height": "100vh"},
        children=[
            # Sidebar
            html.Div(
                style={
                    "width": "280px",
                    "padding": "20px",
                    "backgroundColor": "#1e1e2e",
                    "color": "#cdd6f4",
                    "overflowY": "auto",
                },
                children=[
                    html.H2("Torque Cell DAQ", style={"marginBottom": "20px"}),
                    # Mode selector
                    html.Label("Mode"),
                    dcc.Dropdown(
                        id="mode-selector",
                        options=[
                            {"label": "One-Shot", "value": "one_shot"},
                            {"label": "Timed Test", "value": "timed"},
                            {"label": "Continuous", "value": "continuous"},
                        ],
                        value="continuous",
                        clearable=False,
                        style={"color": "#1e1e2e", "marginBottom": "15px"},
                    ),
                    # Timed duration (shown only in timed mode)
                    html.Div(
                        id="timed-duration-container",
                        style={"display": "none", "marginBottom": "15px"},
                        children=[
                            html.Label("Duration (seconds)"),
                            dcc.Input(
                                id="timed-duration",
                                type="number",
                                value=10,
                                min=1,
                                max=3600,
                                style={"width": "100%"},
                            ),
                        ],
                    ),
                    # Channel
                    html.Label("Channel"),
                    dcc.Dropdown(
                        id="channel-selector",
                        options=[{"label": ch, "value": ch} for ch in AVAILABLE_CHANNELS],
                        value=DEFAULT_CHANNEL,
                        clearable=False,
                        style={"color": "#1e1e2e", "marginBottom": "15px"},
                    ),
                    # Sample rate
                    html.Label("Sample Rate (Hz)"),
                    dcc.Input(
                        id="sample-rate-input",
                        type="number",
                        value=DEFAULT_SAMPLE_RATE,
                        min=1,
                        max=50000,
                        style={"width": "100%", "marginBottom": "15px"},
                    ),
                    # Voltage range
                    html.Label("Voltage Range"),
                    dcc.Dropdown(
                        id="voltage-range-selector",
                        options=[{"label": f"±{v}V", "value": v} for v in VALID_VOLTAGE_RANGES],
                        value=5.0,
                        clearable=False,
                        style={"color": "#1e1e2e", "marginBottom": "15px"},
                    ),
                    html.Hr(),
                    # Calibration
                    html.H4("Calibration"),
                    dcc.Dropdown(
                        id="calibration-mode",
                        options=[
                            {"label": "Raw Voltage", "value": "none"},
                            {"label": "Linear (manual)", "value": "linear"},
                            {"label": "From File", "value": "file"},
                        ],
                        value="none",
                        clearable=False,
                        style={"color": "#1e1e2e", "marginBottom": "15px"},
                    ),
                    # Linear calibration inputs
                    html.Div(
                        id="linear-cal-container",
                        style={"display": "none"},
                        children=[
                            html.Label("Slope (torque/volt)"),
                            dcc.Input(id="cal-slope", type="number", value=1.0, style={"width": "100%"}),
                            html.Label("Offset (Nm)"),
                            dcc.Input(
                                id="cal-offset",
                                type="number",
                                value=0.0,
                                style={"width": "100%", "marginBottom": "15px"},
                            ),
                        ],
                    ),
                    # File calibration upload
                    html.Div(
                        id="file-cal-container",
                        style={"display": "none"},
                        children=[
                            dcc.Upload(
                                id="cal-file-upload",
                                children=html.Button("Upload Calibration CSV"),
                                style={"marginBottom": "15px"},
                            ),
                            html.Div(id="cal-file-status"),
                        ],
                    ),
                    html.Hr(),
                    # Controls
                    html.Div(
                        style={"display": "flex", "gap": "10px", "marginBottom": "15px"},
                        children=[
                            html.Button(
                                "Start",
                                id="start-btn",
                                n_clicks=0,
                                style={
                                    "flex": "1",
                                    "padding": "10px",
                                    "backgroundColor": "#a6e3a1",
                                    "border": "none",
                                    "borderRadius": "5px",
                                    "cursor": "pointer",
                                    "fontWeight": "bold",
                                },
                            ),
                            html.Button(
                                "Stop",
                                id="stop-btn",
                                n_clicks=0,
                                style={
                                    "flex": "1",
                                    "padding": "10px",
                                    "backgroundColor": "#f38ba8",
                                    "border": "none",
                                    "borderRadius": "5px",
                                    "cursor": "pointer",
                                    "fontWeight": "bold",
                                },
                            ),
                        ],
                    ),
                    html.Button(
                        "Export CSV",
                        id="export-btn",
                        n_clicks=0,
                        style={
                            "width": "100%",
                            "padding": "10px",
                            "backgroundColor": "#89b4fa",
                            "border": "none",
                            "borderRadius": "5px",
                            "cursor": "pointer",
                            "fontWeight": "bold",
                        },
                    ),
                    dcc.Download(id="csv-download"),
                ],
            ),
            # Main content
            html.Div(
                style={"flex": "1", "padding": "20px", "backgroundColor": "#181825", "color": "#cdd6f4"},
                children=[
                    # Status bar
                    html.Div(
                        id="status-bar",
                        style={
                            "display": "flex",
                            "gap": "30px",
                            "padding": "10px 15px",
                            "backgroundColor": "#313244",
                            "borderRadius": "8px",
                            "marginBottom": "15px",
                        },
                        children=[
                            html.Span(id="status-connection", children="● Disconnected"),
                            html.Span(id="status-value", children="-- V"),
                            html.Span(id="status-elapsed", children="0.0 s"),
                            html.Span(id="status-samples", children="0 samples"),
                        ],
                    ),
                    # Live plot
                    dcc.Graph(
                        id="live-plot",
                        style={"height": "55vh"},
                        config={"displayModeBar": True, "scrollZoom": True},
                    ),
                    # Data table
                    html.Div(
                        style={"marginTop": "15px", "maxHeight": "25vh", "overflowY": "auto"},
                        children=[
                            html.Table(
                                id="data-table",
                                style={"width": "100%", "borderCollapse": "collapse"},
                            ),
                        ],
                    ),
                    # Interval for live updates
                    dcc.Interval(id="update-interval", interval=250, n_intervals=0, disabled=True),
                    # Hidden stores
                    dcc.Store(id="session-state", data={"running": False, "demo_mode": False}),
                ],
            ),
        ],
    )
```

- [ ] **Step 2: Verify layout imports cleanly**

Run: `python -c "from layout import create_layout; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add layout.py
git commit -m "feat: add Dash layout with sidebar, plot, controls, and status bar"
```

---

### Task 6: Dash Callbacks

**Files:**
- Create: `callbacks.py`

- [ ] **Step 1: Write callbacks.py**

```python
# callbacks.py
from __future__ import annotations

import base64
import io
import os
import queue
import threading
from collections import deque
from typing import TYPE_CHECKING

import plotly.graph_objs as go
from dash import Input, Output, State, callback_context, no_update

from calibration import Calibration
from config import DAQConfig, PLOT_UPDATE_INTERVAL_MS
from daq import DAQReader
from logger import DataLogger

if TYPE_CHECKING:
    from dash import Dash


# Module-level shared state
_data_queue: queue.Queue = queue.Queue()
_plot_buffer: deque = deque(maxlen=5000)
_stop_event: threading.Event = threading.Event()
_error_event: threading.Event = threading.Event()
_reader: DAQReader | None = None
_logger_thread: DataLogger | None = None
_calibration: Calibration = Calibration()


def register_callbacks(app: Dash) -> None:

    @app.callback(
        Output("timed-duration-container", "style"),
        Input("mode-selector", "value"),
    )
    def toggle_timed_duration(mode: str):
        if mode == "timed":
            return {"display": "block", "marginBottom": "15px"}
        return {"display": "none", "marginBottom": "15px"}

    @app.callback(
        Output("linear-cal-container", "style"),
        Output("file-cal-container", "style"),
        Input("calibration-mode", "value"),
    )
    def toggle_calibration_inputs(cal_mode: str):
        linear_style = {"display": "none"}
        file_style = {"display": "none"}
        if cal_mode == "linear":
            linear_style = {"display": "block"}
        elif cal_mode == "file":
            file_style = {"display": "block"}
        return linear_style, file_style

    @app.callback(
        Output("cal-file-status", "children"),
        Input("cal-file-upload", "contents"),
        State("cal-file-upload", "filename"),
    )
    def handle_calibration_upload(contents, filename):
        global _calibration
        if contents is None:
            return no_update
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string).decode("utf-8")
        temp_path = os.path.join("calibration_files", filename)
        os.makedirs("calibration_files", exist_ok=True)
        with open(temp_path, "w") as f:
            f.write(decoded)
        _calibration = Calibration.from_file(temp_path)
        return f"Loaded: {filename}"

    @app.callback(
        Output("session-state", "data"),
        Output("update-interval", "disabled"),
        Input("start-btn", "n_clicks"),
        Input("stop-btn", "n_clicks"),
        State("mode-selector", "value"),
        State("channel-selector", "value"),
        State("sample-rate-input", "value"),
        State("voltage-range-selector", "value"),
        State("timed-duration", "value"),
        State("calibration-mode", "value"),
        State("cal-slope", "value"),
        State("cal-offset", "value"),
        State("session-state", "data"),
    )
    def handle_start_stop(
        start_clicks,
        stop_clicks,
        mode,
        channel,
        sample_rate,
        voltage_range,
        timed_duration,
        cal_mode,
        cal_slope,
        cal_offset,
        session_state,
    ):
        global _reader, _logger_thread, _calibration, _data_queue, _plot_buffer
        global _stop_event, _error_event

        ctx = callback_context
        if not ctx.triggered:
            return no_update, no_update
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "start-btn":
            if session_state.get("running"):
                return no_update, no_update

            _stop_event.clear()
            _error_event.clear()
            _data_queue = queue.Queue()
            _plot_buffer.clear()

            config = DAQConfig(
                channel=channel,
                sample_rate=float(sample_rate or 100),
                voltage_range=float(voltage_range or 5.0),
                mode=mode,
                timed_duration_s=float(timed_duration or 10),
            )

            if cal_mode == "linear":
                _calibration = Calibration(
                    mode="linear",
                    slope=float(cal_slope or 1.0),
                    offset=float(cal_offset or 0.0),
                )
            elif cal_mode == "none":
                _calibration = Calibration()

            try:
                import nidaqmx
                nidaqmx.system.System.local().devices
                demo_mode = False
            except Exception:
                demo_mode = True

            _reader = DAQReader(
                config=config,
                data_queue=_data_queue,
                plot_buffer=_plot_buffer,
                stop_event=_stop_event,
                error_event=_error_event,
                demo_mode=demo_mode,
            )
            _logger_thread = DataLogger(
                config=config,
                data_queue=_data_queue,
                stop_event=_stop_event,
                output_dir=config.csv_dir,
                calibration=_calibration,
            )
            _reader.start()
            _logger_thread.start()

            if mode == "timed":
                duration = float(timed_duration or 10)
                timer = threading.Timer(duration, lambda: _stop_event.set())
                timer.daemon = True
                timer.start()

            return {"running": True, "demo_mode": demo_mode}, False

        elif trigger_id == "stop-btn":
            _stop_event.set()
            return {"running": False, "demo_mode": False}, True

        return no_update, no_update

    @app.callback(
        Output("live-plot", "figure"),
        Output("status-connection", "children"),
        Output("status-value", "children"),
        Output("status-elapsed", "children"),
        Output("status-samples", "children"),
        Output("data-table", "children"),
        Input("update-interval", "n_intervals"),
        State("session-state", "data"),
    )
    def update_live_display(n_intervals, session_state):
        samples = list(_plot_buffer)
        if not samples:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#181825",
                plot_bgcolor="#181825",
                xaxis_title="Elapsed Time (s)",
                yaxis_title="Voltage (V)",
                margin=dict(l=50, r=20, t=30, b=50),
            )
            return empty_fig, "● Waiting", "-- V", "0.0 s", "0 samples", []

        elapsed = [s["elapsed_s"] for s in samples]
        voltages = [s["voltage"] for s in samples]

        fig = go.Figure()
        fig.add_trace(go.Scattergl(
            x=elapsed,
            y=voltages,
            mode="lines",
            name="Voltage",
            line=dict(color="#89b4fa", width=1.5),
        ))

        torques = [_calibration.convert(v) for v in voltages]
        if torques and torques[0] is not None:
            fig.add_trace(go.Scattergl(
                x=elapsed,
                y=torques,
                mode="lines",
                name="Torque (Nm)",
                yaxis="y2",
                line=dict(color="#a6e3a1", width=1.5),
            ))
            fig.update_layout(
                yaxis2=dict(
                    title="Torque (Nm)",
                    overlaying="y",
                    side="right",
                    showgrid=False,
                ),
            )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#181825",
            plot_bgcolor="#181825",
            xaxis_title="Elapsed Time (s)",
            yaxis_title="Voltage (V)",
            margin=dict(l=50, r=50, t=30, b=50),
            legend=dict(x=0, y=1.1, orientation="h"),
        )

        latest = samples[-1]
        is_running = session_state.get("running", False)
        demo = session_state.get("demo_mode", False)
        conn_str = "● Demo Mode" if demo else ("● Connected" if is_running else "● Stopped")
        conn_style = {"color": "#f9e2af"} if demo else (
            {"color": "#a6e3a1"} if is_running else {"color": "#f38ba8"}
        )
        value_str = f"{latest['voltage']:.4f} V"
        elapsed_str = f"{latest['elapsed_s']:.1f} s"
        count_str = f"{len(samples)} samples"

        header = html.Tr([
            html.Th("Timestamp", style={"padding": "5px", "borderBottom": "1px solid #45475a"}),
            html.Th("Elapsed (s)", style={"padding": "5px", "borderBottom": "1px solid #45475a"}),
            html.Th("Voltage (V)", style={"padding": "5px", "borderBottom": "1px solid #45475a"}),
        ])
        rows = []
        for s in samples[-10:]:
            rows.append(html.Tr([
                html.Td(s["timestamp"], style={"padding": "3px"}),
                html.Td(f"{s['elapsed_s']:.4f}", style={"padding": "3px"}),
                html.Td(f"{s['voltage']:.6f}", style={"padding": "3px"}),
            ]))
        table = [html.Thead(header), html.Tbody(rows)]

        return fig, html.Span(conn_str, style=conn_style), value_str, elapsed_str, count_str, table

    @app.callback(
        Output("csv-download", "data"),
        Input("export-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def export_csv(n_clicks):
        samples = list(_plot_buffer)
        if not samples:
            return no_update
        lines = ["timestamp,elapsed_s,voltage_V,torque_Nm\n"]
        for s in samples:
            torque = _calibration.convert(s["voltage"])
            torque_str = f"{torque:.4f}" if torque is not None else ""
            lines.append(
                f"{s['timestamp']},{s['elapsed_s']:.6f},{s['voltage']:.6f},{torque_str}\n"
            )
        content = "".join(lines)
        return dict(content=content, filename="torque_export.csv")


# Need html import for table rendering
from dash import html
```

- [ ] **Step 2: Verify callbacks import cleanly**

Run: `python -c "from callbacks import register_callbacks; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add callbacks.py
git commit -m "feat: add Dash callbacks for start/stop, live plot, calibration, and export"
```

---

### Task 7: App Entry Point

**Files:**
- Create: `app.py`

- [ ] **Step 1: Write app.py**

```python
# app.py
from dash import Dash

from callbacks import register_callbacks
from layout import create_layout


def create_app() -> Dash:
    app = Dash(__name__)
    app.title = "Torque Cell DAQ"
    app.layout = create_layout()
    register_callbacks(app)
    return app


if __name__ == "__main__":
    app = create_app()
    print("Starting Torque Cell DAQ Dashboard...")
    print("Open http://localhost:8050 in your browser")
    app.run(debug=True, host="0.0.0.0", port=8050)
```

- [ ] **Step 2: Smoke test — verify app starts**

Run: `timeout 5 python app.py || true`
Expected: Prints "Starting Torque Cell DAQ Dashboard..." and starts serving (times out after 5s — that's fine, means it's running)

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add app entry point wiring layout and callbacks"
```

---

### Task 8: Create data and calibration_files directories

**Files:**
- Create: `data/.gitkeep`
- Create: `calibration_files/.gitkeep`
- Create: `.gitignore`

- [ ] **Step 1: Create directories and gitignore**

```bash
mkdir -p data calibration_files
touch data/.gitkeep calibration_files/.gitkeep
```

Write `.gitignore`:
```
venv/
__pycache__/
*.pyc
.superpowers/
data/*.csv
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore data/.gitkeep calibration_files/.gitkeep
git commit -m "chore: add data directories and gitignore"
```

---

### Task 9: Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import queue
import threading
import time
from collections import deque

from config import DAQConfig
from calibration import Calibration
from daq import DAQReader
from logger import DataLogger


def test_full_pipeline_demo_mode(tmp_path):
    """Start DAQ reader and logger in demo mode, verify CSV output."""
    cfg = DAQConfig(sample_rate=100, mode="continuous")
    cal = Calibration(mode="linear", slope=10.0, offset=0.0)

    data_queue = queue.Queue()
    plot_buffer = deque(maxlen=500)
    stop_event = threading.Event()
    error_event = threading.Event()

    reader = DAQReader(
        config=cfg,
        data_queue=data_queue,
        plot_buffer=plot_buffer,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=True,
    )
    logger = DataLogger(
        config=cfg,
        data_queue=data_queue,
        stop_event=stop_event,
        output_dir=str(tmp_path),
        calibration=cal,
    )

    reader.start()
    logger.start()
    time.sleep(0.5)
    stop_event.set()
    reader.join(timeout=2.0)
    logger.join(timeout=2.0)

    assert not reader.is_alive()
    assert not logger.is_alive()
    assert not error_event.is_set()
    assert len(plot_buffer) > 10

    csv_files = list(tmp_path.glob("torque_log_*.csv"))
    assert len(csv_files) == 1

    content = csv_files[0].read_text()
    assert "timestamp,elapsed_s,voltage_V,torque_Nm" in content
    lines = [l for l in content.split("\n") if l and not l.startswith("#")]
    data_lines = lines[1:]  # skip header
    assert len(data_lines) > 10

    first_data = data_lines[0].split(",")
    assert len(first_data) == 4
    assert first_data[3] != ""  # torque should be populated


def test_dash_app_creates():
    """Verify the Dash app initializes without errors."""
    from app import create_app
    app = create_app()
    assert app.title == "Torque Cell DAQ"
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: Both tests PASS

- [ ] **Step 3: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full pipeline and Dash app init"
```
