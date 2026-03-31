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
