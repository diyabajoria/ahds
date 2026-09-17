from models.disk import DiskConfig
from simulation.admission import check_admission, effective_bandwidth_bytes_per_ms


def test_admission_accepted_just_under_capacity():
    disk = DiskConfig(cylinders=200, initial_head=0, rpm=7200, bytes_per_track=1_048_576, seek_coeff=0.1)
    avg_bytes = 8192.0
    rt_max = 0.5
    eff_bw = effective_bandwidth_bytes_per_ms(disk, avg_bytes)
    usable = eff_bw * rt_max
    result = check_admission(disk, avg_bytes, rt_max, reserved_bitrates=[], new_bitrate=usable * 0.9)
    assert result.accepted is True


def test_admission_rejected_just_over_capacity():
    disk = DiskConfig(cylinders=200, initial_head=0, rpm=7200, bytes_per_track=1_048_576, seek_coeff=0.1)
    avg_bytes = 8192.0
    rt_max = 0.5
    eff_bw = effective_bandwidth_bytes_per_ms(disk, avg_bytes)
    usable = eff_bw * rt_max
    result = check_admission(disk, avg_bytes, rt_max, reserved_bitrates=[], new_bitrate=usable * 1.1)
    assert result.accepted is False
