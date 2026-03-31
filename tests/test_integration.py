import queue
import threading
import time
from collections import deque

from config import DAQConfig
from calibration import Calibration
from daq import DAQReader
from logger import DataLogger


def test_full_pipeline_demo_mode(tmp_path):
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
    data_lines = lines[1:]
    assert len(data_lines) > 10

    first_data = data_lines[0].split(",")
    assert len(first_data) == 4
    assert first_data[3] != ""


def test_dash_app_creates():
    from app import create_app
    app = create_app()
    assert app.title == "Torque Cell DAQ"
