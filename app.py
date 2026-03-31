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
    print("If accessing from another device, ensure the port is allowed through the firewall.")
    print()
    print("If you get a socket permissions error, try running as Administrator")
    print("or set a custom port: python app.py --port 8060")

    import sys
    port = 8050
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    app.run(debug=True, host="0.0.0.0", port=port)
