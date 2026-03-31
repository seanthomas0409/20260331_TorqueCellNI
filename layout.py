# layout.py
from dash import dcc, html

from config import AVAILABLE_CHANNELS, DEFAULT_CHANNEL, DEFAULT_SAMPLE_RATE, VALID_VOLTAGE_RANGES

# -- Reusable style constants --
FONT = "'Segoe UI', system-ui, -apple-system, sans-serif"
BG_BASE = "#11111b"
BG_SURFACE = "#1e1e2e"
BG_SIDEBAR = "#181825"
BORDER = "#313244"
TEXT_PRIMARY = "#cdd6f4"
TEXT_SECONDARY = "#6c7086"
TEXT_DIM = "#585b70"
ACCENT_BLUE = "#89b4fa"
ACCENT_GREEN = "#a6e3a1"
ACCENT_RED = "#f38ba8"
ACCENT_YELLOW = "#f9e2af"
ACCENT_PEACH = "#fab387"

CARD_STYLE = {
    "background": BG_SURFACE,
    "borderRadius": "14px",
    "padding": "20px",
    "border": f"1px solid {BORDER}",
}
DROPDOWN_STYLE = {"color": BG_SURFACE, "marginBottom": "12px", "fontSize": "13px"}
INPUT_STYLE = {
    "width": "100%",
    "marginBottom": "12px",
    "background": "#313244",
    "border": f"1px solid #45475a",
    "color": TEXT_PRIMARY,
    "padding": "8px 12px",
    "borderRadius": "8px",
    "fontSize": "13px",
}
LABEL_STYLE = {
    "display": "block",
    "fontSize": "11px",
    "color": TEXT_SECONDARY,
    "marginBottom": "4px",
    "textTransform": "uppercase",
    "letterSpacing": "0.5px",
}


def _nav_item(icon: str, label: str, active: bool = False) -> html.Div:
    style = {
        "display": "flex",
        "alignItems": "center",
        "gap": "12px",
        "padding": "10px 12px",
        "borderRadius": "10px",
        "marginBottom": "4px",
        "fontSize": "14px",
        "cursor": "pointer",
    }
    if active:
        style["background"] = "rgba(137, 180, 250, 0.12)"
        style["color"] = ACCENT_BLUE
    else:
        style["color"] = TEXT_SECONDARY
    return html.Div(
        style=style,
        children=[html.Span(icon, style={"fontSize": "16px", "width": "20px", "textAlign": "center"}), label],
    )


def _kpi_card(card_id: str, label: str, badge_text: str, badge_color: str, value: str, sub: str) -> html.Div:
    color_map = {
        "green": f"rgba(166,227,161,0.15)",
        "blue": f"rgba(137,180,250,0.15)",
        "yellow": f"rgba(249,226,175,0.15)",
        "red": f"rgba(243,139,168,0.15)",
    }
    text_map = {"green": ACCENT_GREEN, "blue": ACCENT_BLUE, "yellow": ACCENT_YELLOW, "red": ACCENT_RED}
    return html.Div(
        style=CARD_STYLE,
        children=[
            html.Div(
                style={"fontSize": "12px", "color": TEXT_SECONDARY, "marginBottom": "8px", "display": "flex", "alignItems": "center", "justifyContent": "space-between"},
                children=[
                    label,
                    html.Span(
                        badge_text,
                        style={
                            "fontSize": "11px",
                            "padding": "2px 8px",
                            "borderRadius": "6px",
                            "fontWeight": "600",
                            "background": color_map.get(badge_color, color_map["blue"]),
                            "color": text_map.get(badge_color, text_map["blue"]),
                        },
                    ),
                ],
            ),
            html.Div(id=f"kpi-{card_id}-value", children=value, style={"fontSize": "28px", "fontWeight": "700", "color": TEXT_PRIMARY, "marginBottom": "4px"}),
            html.Div(id=f"kpi-{card_id}-sub", children=sub, style={"fontSize": "11px", "color": TEXT_DIM}),
        ],
    )


def create_layout() -> html.Div:
    return html.Div(
        style={"display": "flex", "fontFamily": FONT, "height": "100vh", "background": BG_BASE, "color": TEXT_PRIMARY},
        children=[
            # ── Sidebar ──
            html.Div(
                style={
                    "width": "220px",
                    "background": BG_SIDEBAR,
                    "padding": "24px 16px",
                    "display": "flex",
                    "flexDirection": "column",
                    "borderRight": f"1px solid {BORDER}",
                    "flexShrink": "0",
                },
                children=[
                    # Logo
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "10px", "padding": "0 8px 24px", "borderBottom": f"1px solid {BORDER}", "marginBottom": "24px"},
                        children=[
                            html.Div(
                                "T",
                                style={
                                    "width": "32px", "height": "32px",
                                    "background": f"linear-gradient(135deg, {ACCENT_RED}, {ACCENT_PEACH})",
                                    "borderRadius": "8px", "display": "flex", "alignItems": "center",
                                    "justifyContent": "center", "fontWeight": "bold", "fontSize": "14px", "color": BG_SURFACE,
                                },
                            ),
                            html.Span("Torque DAQ", style={"fontWeight": "700", "fontSize": "16px"}),
                        ],
                    ),
                    # Nav items
                    _nav_item("\u25C9", "Dashboard", active=True),
                    # Spacer
                    html.Div(style={"flex": "1"}),
                    # Mode section
                    html.Div(
                        "MODE",
                        style={"fontSize": "11px", "textTransform": "uppercase", "color": "#45475a", "padding": "16px 12px 8px", "letterSpacing": "1px"},
                    ),
                    dcc.RadioItems(
                        id="mode-selector",
                        options=[
                            {"label": " Continuous", "value": "continuous"},
                            {"label": " Timed Test", "value": "timed"},
                            {"label": " One-Shot", "value": "one_shot"},
                        ],
                        value="continuous",
                        style={"padding": "0 12px", "fontSize": "14px"},
                        labelStyle={"display": "block", "padding": "8px 0", "cursor": "pointer", "color": "#ffffff"},
                        inputStyle={"marginRight": "10px", "accentColor": ACCENT_BLUE},
                    ),
                    # Timed duration (shown only in timed mode)
                    html.Div(
                        id="timed-duration-container",
                        style={"display": "none", "padding": "8px 12px"},
                        children=[
                            html.Label("Duration (s)", style=LABEL_STYLE),
                            dcc.Input(id="timed-duration", type="number", value=10, min=1, max=3600, style=INPUT_STYLE),
                        ],
                    ),
                ],
            ),

            # ── Main content ──
            html.Div(
                style={"flex": "1", "overflowY": "auto", "padding": "24px", "display": "flex", "flexDirection": "column", "gap": "20px"},
                children=[
                    # Top bar
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "gap": "16px"},
                        children=[
                            html.Div("Dashboard", style={"fontSize": "22px", "fontWeight": "700", "flex": "1"}),
                            html.Div(
                                id="topbar-config-badge",
                                style={"background": "#313244", "padding": "8px 16px", "borderRadius": "10px", "fontSize": "13px", "color": "#a6adc8"},
                            ),
                            html.Div(
                                id="topbar-status-badge",
                                style={"padding": "8px 16px", "borderRadius": "10px", "fontSize": "13px"},
                            ),
                            html.Button(
                                "Start Recording",
                                id="toggle-btn",
                                n_clicks=0,
                                style={
                                    "padding": "10px 20px",
                                    "border": "none",
                                    "borderRadius": "10px",
                                    "fontWeight": "600",
                                    "fontSize": "14px",
                                    "cursor": "pointer",
                                    "backgroundColor": ACCENT_GREEN,
                                    "color": BG_SURFACE,
                                },
                            ),
                        ],
                    ),

                    # KPI cards
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "repeat(4, 1fr)", "gap": "16px"},
                        children=[
                            _kpi_card("voltage", "Current Voltage", "LIVE", "green", "-- V", "Waiting for data"),
                            _kpi_card("torque", "Current Torque", "N/A", "blue", "-- Nm", "No calibration"),
                            _kpi_card("elapsed", "Elapsed Time", "Idle", "yellow", "0.0 s", "Not recording"),
                            _kpi_card("samples", "Samples", "Idle", "red", "0", "No data"),
                        ],
                    ),

                    # Main chart card
                    html.Div(
                        style=CARD_STYLE,
                        children=[
                            html.Div(
                                style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "8px"},
                                children=[
                                    html.Div("Live Signal", style={"fontSize": "15px", "fontWeight": "600"}),
                                    html.Div(
                                        style={"display": "flex", "gap": "16px", "fontSize": "12px", "color": TEXT_SECONDARY},
                                        children=[
                                            html.Span([
                                                html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "borderRadius": "50%", "background": ACCENT_BLUE, "marginRight": "6px"}),
                                                "Voltage (V)",
                                            ]),
                                            html.Span([
                                                html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "borderRadius": "50%", "background": ACCENT_GREEN, "marginRight": "6px"}),
                                                "Torque (Nm)",
                                            ]),
                                        ],
                                    ),
                                ],
                            ),
                            dcc.Graph(
                                id="live-plot",
                                style={"height": "38vh"},
                                config={"displayModeBar": True, "scrollZoom": True},
                            ),
                        ],
                    ),

                    # Bottom row: settings + data table
                    html.Div(
                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px"},
                        children=[
                            # Settings card
                            html.Div(
                                id="settings-card",
                                style=CARD_STYLE,
                                children=[
                                    html.Div(
                                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"},
                                        children=[
                                            html.Div("Acquisition Settings", style={"fontSize": "15px", "fontWeight": "600"}),
                                            html.Button(
                                                "Export CSV",
                                                id="export-btn",
                                                n_clicks=0,
                                                style={
                                                    "background": ACCENT_BLUE, "color": BG_SURFACE,
                                                    "border": "none", "borderRadius": "8px",
                                                    "padding": "6px 14px", "fontSize": "12px",
                                                    "fontWeight": "600", "cursor": "pointer",
                                                },
                                            ),
                                        ],
                                    ),
                                    dcc.Download(id="csv-download"),
                                    html.Div(
                                        style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px"},
                                        children=[
                                            html.Div([
                                                html.Label("Channel", style=LABEL_STYLE),
                                                dcc.Dropdown(
                                                    id="channel-selector",
                                                    options=[{"label": ch, "value": ch} for ch in AVAILABLE_CHANNELS],
                                                    value=DEFAULT_CHANNEL,
                                                    clearable=False,
                                                    style=DROPDOWN_STYLE,
                                                ),
                                            ]),
                                            html.Div([
                                                html.Label("Sample Rate (Hz)", style=LABEL_STYLE),
                                                dcc.Input(
                                                    id="sample-rate-input",
                                                    type="number",
                                                    value=DEFAULT_SAMPLE_RATE,
                                                    min=1,
                                                    max=50000,
                                                    style=INPUT_STYLE,
                                                ),
                                            ]),
                                            html.Div([
                                                html.Label("Voltage Range", style=LABEL_STYLE),
                                                dcc.Dropdown(
                                                    id="voltage-range-selector",
                                                    options=[{"label": f"\u00b1{v}V", "value": v} for v in VALID_VOLTAGE_RANGES],
                                                    value=5.0,
                                                    clearable=False,
                                                    style=DROPDOWN_STYLE,
                                                ),
                                            ]),
                                            html.Div(id="calibration-section", children=[
                                                html.Label("Calibration", style=LABEL_STYLE),
                                                dcc.Dropdown(
                                                    id="calibration-mode",
                                                    options=[
                                                        {"label": "Raw Voltage", "value": "none"},
                                                        {"label": "Linear (manual)", "value": "linear"},
                                                        {"label": "From File", "value": "file"},
                                                    ],
                                                    value="none",
                                                    clearable=False,
                                                    style=DROPDOWN_STYLE,
                                                ),
                                            ]),
                                        ],
                                    ),
                                    # Linear cal inputs
                                    html.Div(
                                        id="linear-cal-container",
                                        style={"display": "none"},
                                        children=[
                                            html.Div(
                                                style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "12px", "marginTop": "4px"},
                                                children=[
                                                    html.Div([
                                                        html.Label("Slope (torque/volt)", style=LABEL_STYLE),
                                                        dcc.Input(id="cal-slope", type="number", value=1.0, style=INPUT_STYLE),
                                                    ]),
                                                    html.Div([
                                                        html.Label("Offset (Nm)", style=LABEL_STYLE),
                                                        dcc.Input(id="cal-offset", type="number", value=0.0, style=INPUT_STYLE),
                                                    ]),
                                                ],
                                            ),
                                        ],
                                    ),
                                    # File cal upload
                                    html.Div(
                                        id="file-cal-container",
                                        style={"display": "none"},
                                        children=[
                                            dcc.Upload(
                                                id="cal-file-upload",
                                                children=html.Button(
                                                    "Upload Calibration CSV",
                                                    style={
                                                        "background": "#313244", "color": TEXT_PRIMARY,
                                                        "border": f"1px dashed #45475a", "borderRadius": "8px",
                                                        "padding": "8px 16px", "fontSize": "12px", "cursor": "pointer",
                                                        "width": "100%", "marginTop": "4px",
                                                    },
                                                ),
                                            ),
                                            html.Div(id="cal-file-status", style={"fontSize": "12px", "color": ACCENT_GREEN, "marginTop": "6px"}),
                                        ],
                                    ),
                                ],
                            ),

                            # Data table card
                            html.Div(
                                style=CARD_STYLE,
                                children=[
                                    html.Div(
                                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "16px"},
                                        children=[
                                            html.Div("Recent Readings", style={"fontSize": "15px", "fontWeight": "600"}),
                                            html.Span("Last 10 samples", style={"fontSize": "12px", "color": TEXT_SECONDARY}),
                                        ],
                                    ),
                                    html.Div(
                                        style={"overflowY": "auto", "maxHeight": "240px"},
                                        children=[
                                            html.Table(
                                                id="data-table",
                                                style={"width": "100%", "borderCollapse": "collapse", "fontSize": "13px"},
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),

            # Hidden state
            dcc.Interval(id="update-interval", interval=250, n_intervals=0, disabled=True),
            dcc.Store(id="session-state", data={"running": False, "demo_mode": False}),
        ],
    )
