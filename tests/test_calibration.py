import os
import tempfile
import numpy as np
from calibration import Calibration


def test_no_calibration_returns_none():
    cal = Calibration()
    assert cal.convert(2.5) is None


def test_linear_calibration():
    cal = Calibration(mode="linear", slope=10.0, offset=0.0)
    assert cal.convert(2.5) == 25.0
    assert cal.convert(0.0) == 0.0
    assert cal.convert(5.0) == 50.0


def test_linear_calibration_with_offset():
    cal = Calibration(mode="linear", slope=10.0, offset=-5.0)
    assert cal.convert(2.5) == 20.0


def test_linear_from_range():
    cal = Calibration.from_range(
        voltage_min=0.0, voltage_max=5.0,
        torque_min=0.0, torque_max=100.0,
    )
    assert cal.convert(2.5) == 50.0
    assert cal.convert(0.0) == 0.0
    assert cal.convert(5.0) == 100.0


def test_file_calibration():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("voltage,torque\n")
        f.write("0.0,0.0\n")
        f.write("2.5,50.0\n")
        f.write("5.0,100.0\n")
        path = f.name
    try:
        cal = Calibration.from_file(path)
        assert cal.convert(1.25) == 25.0
        assert cal.convert(0.0) == 0.0
        assert cal.convert(5.0) == 100.0
    finally:
        os.unlink(path)


def test_convert_array():
    cal = Calibration(mode="linear", slope=10.0, offset=0.0)
    voltages = np.array([0.0, 1.0, 2.0, 3.0])
    result = cal.convert_array(voltages)
    np.testing.assert_array_equal(result, np.array([0.0, 10.0, 20.0, 30.0]))


def test_convert_array_no_calibration():
    cal = Calibration()
    voltages = np.array([1.0, 2.0])
    assert cal.convert_array(voltages) is None
