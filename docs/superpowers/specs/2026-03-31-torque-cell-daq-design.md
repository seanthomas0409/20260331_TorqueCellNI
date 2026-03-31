# Torque Cell DAQ — Design Spec

## Overview

A Python-based data acquisition tool for reading, logging, saving, and visualizing analog torque signals from a DYJN-104 load cell (with 510 weight transmitter) via an NI USB-6002 DAQ. The tool provides a web-based dashboard (Plotly Dash) with three operating modes: one-shot measurement, timed test, and continuous monitoring.

## Hardware

| Component | Details |
|---|---|
| **DAQ** | NI USB-6002 — 8 SE / 4 diff AI channels, 12-bit, 50 kS/s max aggregate |
| **Sensor** | DYJN-104 rotary torque sensor |
| **Signal conditioner** | 510 weight transmitter — outputs 0–5V or 0–10V analog |

## Architecture: Threaded Producer-Consumer

Single Python process with three threads:

| Thread | Role | Communication |
|---|---|---|
| **DAQ Thread** | Reads analog samples from NI USB-6002 via `nidaqmx` | Pushes to `queue.Queue` (for logger) and `collections.deque` (for live plot) |
| **Logger Thread** | Consumes from queue, writes timestamped CSV | Reads from `queue.Queue` |
| **Main Thread** | Runs Dash web server, handles UI callbacks | Reads from `collections.deque` via `dcc.Interval` |

**Coordination:** `threading.Event` flags for start, stop, pause, and error signaling between threads.

**Why threading:** The `nidaqmx` read calls are I/O-bound (USB hardware waits), so the GIL is not a bottleneck. DAQ and Dash naturally alternate without contention.

## Operating Modes

1. **One-Shot** — Click "Read", display a single voltage/torque value prominently on screen.
2. **Timed Test** — Set duration, click "Start", auto-stops when time elapses, saves CSV.
3. **Continuous** — Click "Start", runs indefinitely with live rolling plot until "Stop" is pressed, saves CSV.

## Dashboard Layout (Plotly Dash)

| Panel | Contents |
|---|---|
| **Settings sidebar** | Channel selector (AI0–AI7), sample rate input (with USB-6002 max as limit), voltage range (±1V/±2V/±5V/±10V), calibration config |
| **Live Plot** | Rolling time-series (Plotly). Voltage (and torque if calibrated). Auto-scaling Y axis. |
| **Status bar** | Connection status, current reading, elapsed time, sample count |
| **Controls** | Start / Stop / Export buttons. Mode selector (one-shot / timed / continuous). |
| **Data table** | Last N readings in a scrollable table below the plot |

## Calibration

Three modes, selectable in the settings sidebar:

1. **Raw voltage** (default) — no conversion, `torque_Nm` column left empty in CSV.
2. **Manual linear** — user enters slope + offset, or min/max voltage mapped to min/max torque.
3. **Calibration file** — upload a CSV with `voltage,torque` pairs. Linear interpolation applied.

## Data Flow & File Management

**CSV format:**
```
# Sample Rate: 100 Hz
# Channel: AI0
# Voltage Range: ±5V
# Calibration: none
# Mode: continuous
# Start Time: 2026-03-31 13:00:00
timestamp,elapsed_s,voltage_V,torque_Nm
2026-03-31 13:00:00.001,0.000,2.341,
2026-03-31 13:00:00.011,0.010,2.356,
```

- Auto-generated filename: `torque_log_YYYYMMDD_HHMMSS.csv`
- Saved to `data/` subdirectory (auto-created)
- Metadata header as commented lines
- Export button in UI triggers browser download of current session CSV

## Sample Rate Configuration

- User-configurable via the dashboard settings panel
- Default: 100 Hz
- Min: 1 Hz
- Max: 50,000 Hz (NI USB-6002 hardware limit, single channel)
- Dashboard validates input against hardware limits
- Note: max aggregate rate is 50 kS/s shared across active channels

## Error Handling

- **DAQ disconnect mid-test:** DAQ thread sets error event, UI shows warning banner, CSV flushed and closed cleanly.
- **No NI device at startup:** Dashboard loads in "demo mode" with simulated sinusoidal data. Useful for UI development and testing without hardware.

## Project Structure

```
20260331_TorqueCellNI/
├── app.py                  # Entry point — starts Dash server
├── daq.py                  # DAQ thread: nidaqmx reads, pushes to queue/buffer
├── logger.py               # Logger thread: consumes queue, writes CSV
├── calibration.py          # Load/apply calibration (linear or file-based)
├── layout.py               # Dash layout definition (sidebar, plot, controls)
├── callbacks.py            # Dash callbacks (start/stop, mode switch, plot update)
├── config.py               # Defaults (sample rate, channel, voltage range, paths)
├── requirements.txt        # Python dependencies
├── data/                   # Auto-created directory for CSV output
└── calibration_files/      # Optional: user-uploaded calibration CSVs
```

## Dependencies

| Package | Purpose |
|---|---|
| `nidaqmx` | NI DAQ hardware interface |
| `dash` | Web dashboard framework |
| `plotly` | Interactive charts |
| `pandas` | CSV handling and data manipulation |
| `numpy` | Numerical operations |

**Python:** 3.9+

## Running

```bash
pip install -r requirements.txt
python app.py
# Dashboard at http://localhost:8050
```
