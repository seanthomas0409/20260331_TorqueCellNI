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
                    html.Label("Channel"),
                    dcc.Dropdown(
                        id="channel-selector",
                        options=[{"label": ch, "value": ch} for ch in AVAILABLE_CHANNELS],
                        value=DEFAULT_CHANNEL,
                        clearable=False,
                        style={"color": "#1e1e2e", "marginBottom": "15px"},
                    ),
                    html.Label("Sample Rate (Hz)"),
                    dcc.Input(
                        id="sample-rate-input",
                        type="number",
                        value=DEFAULT_SAMPLE_RATE,
                        min=1,
                        max=50000,
                        style={"width": "100%", "marginBottom": "15px"},
                    ),
                    html.Label("Voltage Range"),
                    dcc.Dropdown(
                        id="voltage-range-selector",
                        options=[{"label": f"±{v}V", "value": v} for v in VALID_VOLTAGE_RANGES],
                        value=5.0,
                        clearable=False,
                        style={"color": "#1e1e2e", "marginBottom": "15px"},
                    ),
                    html.Hr(),
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
                    html.Button(
                        "Start Recording",
                        id="toggle-btn",
                        n_clicks=0,
                        style={
                            "width": "100%",
                            "padding": "12px",
                            "backgroundColor": "#a6e3a1",
                            "color": "#1e1e2e",
                            "border": "none",
                            "borderRadius": "5px",
                            "cursor": "pointer",
                            "fontWeight": "bold",
                            "fontSize": "14px",
                            "marginBottom": "15px",
                        },
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
                    dcc.Graph(
                        id="live-plot",
                        style={"height": "55vh"},
                        config={"displayModeBar": True, "scrollZoom": True},
                    ),
                    html.Div(
                        style={"marginTop": "15px", "maxHeight": "25vh", "overflowY": "auto"},
                        children=[
                            html.Table(
                                id="data-table",
                                style={"width": "100%", "borderCollapse": "collapse"},
                            ),
                        ],
                    ),
                    dcc.Interval(id="update-interval", interval=250, n_intervals=0, disabled=True),
                    dcc.Store(id="session-state", data={"running": False, "demo_mode": False}),
                ],
            ),
        ],
    )
