from dataclasses import dataclass, field

VALID_VOLTAGE_RANGES = [1.0, 2.0, 5.0, 10.0]
MAX_SAMPLE_RATE = 50000.0
MIN_SAMPLE_RATE = 1.0
DEFAULT_SAMPLE_RATE = 100.0
DEFAULT_CHANNEL = "Dev1/ai0"
DEFAULT_VOLTAGE_RANGE = 5.0
DEFAULT_BUFFER_SIZE = 5000
DEFAULT_CSV_DIR = "data"
def _detect_channels() -> list[str]:
    """Return real NI-DAQmx AI channels if hardware is present, else defaults."""
    try:
        import nidaqmx
        system = nidaqmx.system.System.local()
        channels = []
        for device in system.devices:
            channels.extend(ch.name for ch in device.ai_physical_channels)
        if channels:
            return channels
    except Exception:
        pass
    return [f"Dev1/ai{i}" for i in range(8)]


def _detect_hardware() -> bool:
    """Return True if any NI-DAQmx device is connected."""
    try:
        import nidaqmx
        return len(nidaqmx.system.System.local().devices) > 0
    except Exception:
        return False


AVAILABLE_CHANNELS = _detect_channels()
HARDWARE_DETECTED = _detect_hardware()
PLOT_UPDATE_INTERVAL_MS = 250


@dataclass
class DAQConfig:
    channel: str = DEFAULT_CHANNEL
    sample_rate: float = DEFAULT_SAMPLE_RATE
    voltage_range: float = DEFAULT_VOLTAGE_RANGE
    buffer_size: int = DEFAULT_BUFFER_SIZE
    csv_dir: str = DEFAULT_CSV_DIR
    mode: str = "continuous"
    timed_duration_s: float = 10.0

    def __post_init__(self):
        self.sample_rate = max(MIN_SAMPLE_RATE, min(self.sample_rate, MAX_SAMPLE_RATE))
        if self.voltage_range not in VALID_VOLTAGE_RANGES:
            self.voltage_range = min(
                VALID_VOLTAGE_RANGES, key=lambda v: v if v >= self.voltage_range else float("inf")
            )
