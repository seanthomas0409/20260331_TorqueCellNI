from config import DAQConfig


def test_default_config():
    cfg = DAQConfig()
    assert cfg.channel == "Dev1/ai0"
    assert cfg.sample_rate == 100.0
    assert cfg.voltage_range == 5.0
    assert cfg.buffer_size == 5000
    assert cfg.csv_dir == "data"


def test_config_validates_sample_rate_max():
    cfg = DAQConfig(sample_rate=60000)
    assert cfg.sample_rate == 50000.0


def test_config_validates_sample_rate_min():
    cfg = DAQConfig(sample_rate=0)
    assert cfg.sample_rate == 1.0


def test_config_voltage_range_options():
    for vr in [1.0, 2.0, 5.0, 10.0]:
        cfg = DAQConfig(voltage_range=vr)
        assert cfg.voltage_range == vr


def test_config_invalid_voltage_range_clamps():
    cfg = DAQConfig(voltage_range=7.0)
    assert cfg.voltage_range == 10.0
