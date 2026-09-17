"""The real (non-heuristic) workload classifier: decision tree vs SVM
baseline, both trained/evaluated on the same split of the same features."""
from models.workload import WorkloadConfig, MultimediaConfig, OLTPConfig, OLAPConfig
from models.disk import DiskConfig
from simulation.workload_builder import build_workload
from simulation.classifier_ml import train_and_evaluate


def test_classifier_reports_precision_recall_f1_for_both_models():
    wcfg = WorkloadConfig(multimedia=MultimediaConfig(n_streams=6), oltp=OLTPConfig(n_requests=250),
                           olap=OLAPConfig(n_scans=6), seed=11)
    requests, _ = build_workload(wcfg, DiskConfig())
    results = train_and_evaluate(requests, seed=11)
    assert set(results.keys()) == {"decision_tree", "svm_baseline"}
    for name, m in results.items():
        assert 0.0 <= m.precision <= 1.0
        assert 0.0 <= m.recall <= 1.0
        assert 0.0 <= m.f1 <= 1.0
        assert len(m.confusion_matrix) == 2 and len(m.confusion_matrix[0]) == 2


def test_classifier_rejects_single_class_workload():
    import pytest
    wcfg = WorkloadConfig(multimedia=MultimediaConfig(n_streams=0), oltp=OLTPConfig(n_requests=0),
                           olap=OLAPConfig(n_scans=3), seed=1)
    requests, _ = build_workload(wcfg, DiskConfig())
    with pytest.raises(ValueError):
        train_and_evaluate(requests, seed=1)
