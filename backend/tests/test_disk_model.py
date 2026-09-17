"""Hand-verified seek/rotation/transfer arithmetic (spec section 9, item 2)."""
from models.disk import DiskConfig, SeekModel, DiskType
from simulation.disk_model import compute_service_time, seek_time_ms


def test_rotation_and_transfer_by_hand():
    # rpm=7200 -> one revolution = 60000/7200 = 8.3333ms; half of that = 4.16667ms
    # bytes_per_track=1048576, size=4096 -> fraction=4096/1048576=0.00390625
    # transfer = 0.00390625 * 8.33333 = 0.032552083...ms
    disk = DiskConfig(rpm=7200, bytes_per_track=1_048_576, seek_coeff=0.15, initial_head=0)
    b = compute_service_time(head=53, target_cylinder=53, size_bytes=4096, disk=disk)  # zero seek
    assert b.seek_time == 0.0
    assert abs(b.rotational_delay - 4.166666666666667) < 1e-9
    assert abs(b.transfer_time - 0.032552083333333336) < 1e-9
    assert abs(b.service_time - (b.rotational_delay + b.transfer_time)) < 1e-9


def test_linear_seek_by_hand():
    disk = DiskConfig(seek_model=SeekModel.LINEAR, seek_coeff=0.15)
    assert seek_time_ms(45, disk) == 0.15 * 45
    assert seek_time_ms(0, disk) == 0.0


def test_realistic_seek_by_hand():
    disk = DiskConfig(seek_model=SeekModel.REALISTIC, seek_a=1.5, seek_b=0.6)
    import math
    assert abs(seek_time_ms(100, disk) - (1.5 + 0.6 * math.sqrt(100))) < 1e-9
    assert seek_time_ms(0, disk) == 0.0  # seek = 0 when d == 0 even in REALISTIC model


def test_ssd_mode_zeroes_seek_and_rotation():
    disk = DiskConfig(disk_type=DiskType.SSD, ssd_bandwidth=2000.0)
    b = compute_service_time(head=10, target_cylinder=400, size_bytes=8192, disk=disk)
    assert b.seek_time == 0.0
    assert b.rotational_delay == 0.0
    assert abs(b.transfer_time - (8192 / 2000.0)) < 1e-9
