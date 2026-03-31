# callbacks.py
from __future__ import annotations

import base64
import os
import queue
import threading
from collections import deque
from typing import TYPE_CHECKING

import plotly.graph_objs as go
from dash import Input, Output, State, callback_context, html, no_update

from calibration import Calibration
from config import DAQConfig
from daq import DAQReader
from logger import DataLogger

if TYPE_CHECKING:
    from dash import Dash

_data_queue: queue.Queue = queue.Queue()
_plot_buffer: deque = deque(maxlen=5000)
_stop_event: threading.Event = threading.Event()
_error_event: threading.Event = threading.Event()
_reader: DAQReader | None = None
_logger_thread: DataLogger | None = None
_calibration: Calibration = Calibration()

# Style constants
_BG_SURFACE = "#1e1e2e"
_ACCENT_GREEN = "#a6e3a1"
_ACCENT_RED = "#f38ba8"
_ACCENT_YELLOW = "#f9e2af"
_ACCENT_BLUE = "#89b4fa"
_TEXT_SEC = "#6c7086"
_TEXT_DIM = "#585b70"

_TOGGLE_BASE = {
    "padding": "10px 20px",
    "border": "none",
    "borderRadius": "10px",
    "fontWeight": "600",
    "fontSize": "14px",
    "cursor": "pointer",
    "color": _BG_SURFACE,
}
_TH_STYLE = {
    "textAlign": "left",
    "padding": "8px 12px",
    "color": _TEXT_SEC,
    "fontWeight": "600",
    "fontSize": "11px",
    "textTransform": "uppercase",
    "letterSpacing": "0.5px",
    "borderBottom": "1px solid #313244",
}
_TD_STYLE = {
    "padding": "8px 12px",
    "borderBottom": "1px solid rgba(49,50,68,0.5)",
    "color": "#bac2de",
}


def register_callbacks(app: Dash) -> None:

    @app.callback(
        Output("timed-duration-container", "style"),
        Input("mode-selector", "value"),
    )
    def toggle_timed_duration(mode: str):
        if mode == "timed":
            return {"display": "block", "padding": "8px 12px"}
        return {"display": "none", "padding": "8px 12px"}

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
        Output("toggle-btn", "children"),
        Output("toggle-btn", "style"),
        Input("toggle-btn", "n_clicks"),
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
    def handle_toggle(
        n_clicks, mode, channel, sample_rate, voltage_range,
        timed_duration, cal_mode, cal_slope, cal_offset, session_state,
    ):
        global _reader, _logger_thread, _calibration, _data_queue, _plot_buffer
        global _stop_event, _error_event

        start_style = {**_TOGGLE_BASE, "backgroundColor": _ACCENT_GREEN}
        stop_style = {**_TOGGLE_BASE, "backgroundColor": _ACCENT_RED}

        if not n_clicks:
            return no_update, no_update, no_update, no_update

        is_running = session_state.get("running", False)

        if not is_running:
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

            return {"running": True, "demo_mode": demo_mode}, False, "Stop Recording", stop_style

        else:
            _stop_event.set()
            return {"running": False, "demo_mode": False}, True, "Start Recording", start_style

    @app.callback(
        Output("live-plot", "figure"),
        Output("topbar-config-badge", "children"),
        Output("topbar-status-badge", "children"),
        Output("topbar-status-badge", "style"),
        Output("kpi-voltage-value", "children"),
        Output("kpi-voltage-sub", "children"),
        Output("kpi-torque-value", "children"),
        Output("kpi-torque-sub", "children"),
        Output("kpi-elapsed-value", "children"),
        Output("kpi-elapsed-sub", "children"),
        Output("kpi-samples-value", "children"),
        Output("kpi-samples-sub", "children"),
        Output("data-table", "children"),
        Input("update-interval", "n_intervals"),
        State("session-state", "data"),
        State("channel-selector", "value"),
        State("sample-rate-input", "value"),
        State("voltage-range-selector", "value"),
    )
    def update_live_display(n_intervals, session_state, channel, sample_rate, voltage_range):
        config_str = f"{channel or 'Dev1/ai0'}  \u2022  {sample_rate or 100} Hz  \u2022  \u00b1{voltage_range or 5}V"

        badge_base = {"padding": "8px 16px", "borderRadius": "10px", "fontSize": "13px"}

        samples = list(_plot_buffer)
        if not samples:
            empty_fig = go.Figure()
            empty_fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#11111b",
                plot_bgcolor="#181825",
                xaxis_title="Elapsed Time (s)",
                yaxis_title="Voltage (V)",
                margin=dict(l=50, r=20, t=10, b=40),
            )
            is_running = session_state.get("running", False)
            status_text = "\u25CF Running" if is_running else "\u25CF Idle"
            status_style = {**badge_base, "color": _ACCENT_GREEN if is_running else _TEXT_SEC, "background": "rgba(166,227,161,0.1)" if is_running else "#313244"}
            return (
                empty_fig, config_str, status_text, status_style,
                "-- V", "Waiting for data",
                "-- Nm", "No calibration" if _calibration.mode == "none" else f"Linear: {_calibration.slope}x + {_calibration.offset}",
                "0.0 s", "Not recording",
                "0", "No data",
                [],
            )

        elapsed = [s["elapsed_s"] for s in samples]
        voltages = [s["voltage"] for s in samples]

        fig = go.Figure()
        fig.add_trace(go.Scattergl(
            x=elapsed, y=voltages, mode="lines", name="Voltage",
            line=dict(color=_ACCENT_BLUE, width=1.5),
        ))

        torques = [_calibration.convert(v) for v in voltages]
        has_torque = torques and torques[0] is not None
        if has_torque:
            fig.add_trace(go.Scattergl(
                x=elapsed, y=torques, mode="lines", name="Torque (Nm)",
                yaxis="y2", line=dict(color=_ACCENT_GREEN, width=1.5),
            ))
            fig.update_layout(
                yaxis2=dict(title="Torque (Nm)", overlaying="y", side="right", showgrid=False),
            )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#11111b",
            plot_bgcolor="#181825",
            xaxis_title="Elapsed Time (s)",
            yaxis_title="Voltage (V)",
            margin=dict(l=50, r=50, t=10, b=40),
            legend=dict(x=0, y=1.12, orientation="h"),
        )

        latest = samples[-1]
        is_running = session_state.get("running", False)
        demo = session_state.get("demo_mode", False)

        if demo:
            status_text = "\u25CF Demo Mode"
            status_style = {**badge_base, "color": _ACCENT_YELLOW, "background": "rgba(249,226,175,0.1)"}
        elif is_running:
            status_text = "\u25CF Connected"
            status_style = {**badge_base, "color": _ACCENT_GREEN, "background": "rgba(166,227,161,0.1)"}
        else:
            status_text = "\u25CF Stopped"
            status_style = {**badge_base, "color": _ACCENT_RED, "background": "rgba(243,139,168,0.1)"}

        voltage_val = f"{latest['voltage']:.4f} V"
        voltage_sub = f"Updated {latest['elapsed_s']:.2f}s"
        torque_val = f"{torques[-1]:.2f} Nm" if has_torque else "-- Nm"
        torque_sub = f"Linear: {_calibration.slope}x + {_calibration.offset}" if _calibration.mode == "linear" else ("File-based" if _calibration.mode == "file" else "No calibration")
        elapsed_val = f"{latest['elapsed_s']:.1f} s"
        elapsed_sub = f"{'Continuous' if session_state.get('running') else 'Stopped'} mode"
        samples_val = f"{len(samples):,}"
        samples_sub = "In plot buffer"

        header = html.Tr([
            html.Th("Timestamp", style=_TH_STYLE),
            html.Th("Elapsed", style=_TH_STYLE),
            html.Th("Voltage", style=_TH_STYLE),
            html.Th("Torque", style=_TH_STYLE),
        ])
        rows = []
        for s in samples[-10:]:
            t = _calibration.convert(s["voltage"])
            t_str = f"{t:.2f} Nm" if t is not None else "--"
            ts = s["timestamp"]
            if "T" in ts:
                ts = ts.split("T")[1][:12]
            rows.append(html.Tr([
                html.Td(ts, style=_TD_STYLE),
                html.Td(f"{s['elapsed_s']:.3f}s", style=_TD_STYLE),
                html.Td(f"{s['voltage']:.4f} V", style=_TD_STYLE),
                html.Td(t_str, style=_TD_STYLE),
            ]))
        table = [html.Thead(header), html.Tbody(rows)]

        return (
            fig, config_str, status_text, status_style,
            voltage_val, voltage_sub,
            torque_val, torque_sub,
            elapsed_val, elapsed_sub,
            samples_val, samples_sub,
            table,
        )

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
            lines.append(f"{s['timestamp']},{s['elapsed_s']:.6f},{s['voltage']:.6f},{torque_str}\n")
        return dict(content="".join(lines), filename="torque_export.csv")
