import queue
import threading
import time
from collections import deque

from daq import DAQReader
from config import DAQConfig


def test_daq_reader_demo_mode_produces_samples():
    q = queue.Queue()
    buf = deque(maxlen=100)
    stop_event = threading.Event()
    error_event = threading.Event()
    cfg = DAQConfig(sample_rate=100)

    reader = DAQReader(
        config=cfg,
        data_queue=q,
        plot_buffer=buf,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=True,
    )
    reader.start()
    time.sleep(0.3)
    stop_event.set()
    reader.join(timeout=2.0)

    assert not reader.is_alive()
    assert q.qsize() > 0
    assert len(buf) > 0


def test_daq_reader_sample_format():
    q = queue.Queue()
    buf = deque(maxlen=100)
    stop_event = threading.Event()
    error_event = threading.Event()
    cfg = DAQConfig(sample_rate=50)

    reader = DAQReader(
        config=cfg,
        data_queue=q,
        plot_buffer=buf,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=True,
    )
    reader.start()
    time.sleep(0.2)
    stop_event.set()
    reader.join(timeout=2.0)

    sample = q.get_nowait()
    assert "timestamp" in sample
    assert "elapsed_s" in sample
    assert "voltage" in sample


def test_daq_reader_stop_event_stops_thread():
    q = queue.Queue()
    buf = deque(maxlen=100)
    stop_event = threading.Event()
    error_event = threading.Event()
    cfg = DAQConfig(sample_rate=100)

    reader = DAQReader(
        config=cfg,
        data_queue=q,
        plot_buffer=buf,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=True,
    )
    reader.start()
    time.sleep(0.1)
    stop_event.set()
    reader.join(timeout=2.0)
    assert not reader.is_alive()


def test_daq_reader_error_event_on_failure():
    q = queue.Queue()
    buf = deque(maxlen=100)
    stop_event = threading.Event()
    error_event = threading.Event()
    cfg = DAQConfig(sample_rate=100, channel="FakeDevice/ai99")

    reader = DAQReader(
        config=cfg,
        data_queue=q,
        plot_buffer=buf,
        stop_event=stop_event,
        error_event=error_event,
        demo_mode=False,
    )
    reader.start()
    reader.join(timeout=3.0)
    assert error_event.is_set()
