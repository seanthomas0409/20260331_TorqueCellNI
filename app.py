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
