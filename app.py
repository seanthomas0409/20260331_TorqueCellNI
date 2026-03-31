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
    import socket

    app = create_app()
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "127.0.0.1"

    print("Starting Torque Cell DAQ Dashboard...")
    print(f"  Local:   http://localhost:8050")
    print(f"  Network: http://{local_ip}:8050")
    print()
    print("If accessing from another device, ensure port 8050 is allowed through the firewall.")
    app.run(debug=True, host="0.0.0.0", port=8050)
