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
        n_clicks,
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

        btn_base = {
            "width": "100%",
            "padding": "12px",
            "border": "none",
            "borderRadius": "5px",
            "cursor": "pointer",
            "fontWeight": "bold",
            "fontSize": "14px",
            "marginBottom": "15px",
        }
        start_style = {**btn_base, "backgroundColor": "#a6e3a1", "color": "#1e1e2e"}
        stop_style = {**btn_base, "backgroundColor": "#f38ba8", "color": "#1e1e2e"}

        if not n_clicks:
            return no_update, no_update, no_update, no_update

        is_running = session_state.get("running", False)

        if not is_running:
            # START recording
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

            return (
                {"running": True, "demo_mode": demo_mode},
                False,
                "Stop Recording",
                stop_style,
            )

        else:
            # STOP recording
            _stop_event.set()
            return (
                {"running": False, "demo_mode": False},
                True,
                "Start Recording",
                start_style,
            )

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

        return fig, conn_str, value_str, elapsed_str, count_str, table

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
