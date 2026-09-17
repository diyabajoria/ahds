"""Workload classifier — spec section 8.4 / Objective 1.

A lightweight decision tree classifies each request as Multimedia or
Database from observable features alone (workloads/features.py),
benchmarked against an SVM baseline, exactly as called for in the review's
methodology. This supersedes the older purely-heuristic classifier
(workloads/classifier.py, kept for reference/comparison) with a real
trained model reporting precision/recall/F1, per Objective 1 and the
Expected Outcome table.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
import numpy as np

from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
from sklearn.preprocessing import StandardScaler

from models.request import Request
from workloads.features import extract_features, FEATURE_NAMES


@dataclass
class ClassifierMetrics:
    model_name: str
    precision: float
    recall: float
    f1: float
    confusion_matrix: List[List[int]]   # [[TN, FP], [FN, TP]], label 1 = MULTIMEDIA
    feature_importances: Dict[str, float] = field(default_factory=dict)


def _eval_model(model, X_test, y_test, name: str) -> ClassifierMetrics:
    y_pred = model.predict(X_test)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", pos_label=1, zero_division=0
    )
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()
    importances = {}
    if hasattr(model, "feature_importances_"):
        importances = dict(zip(FEATURE_NAMES, [float(x) for x in model.feature_importances_]))
    return ClassifierMetrics(
        model_name=name, precision=float(precision), recall=float(recall), f1=float(f1),
        confusion_matrix=cm, feature_importances=importances,
    )


def train_and_evaluate(requests: List[Request], seed: int = 42, test_size: float = 0.3) -> Dict[str, ClassifierMetrics]:
    """Trains a Decision Tree (the primary model) and an SVM (the
    benchmark baseline named in the review's methodology) on the same
    train/test split of the same feature set, and returns both sets of
    metrics so they can be compared directly."""
    X, y = extract_features(requests)
    if len(set(y.tolist())) < 2:
        raise ValueError("workload contains only one class — cannot train/evaluate a 2-class classifier "
                          "(generate both multimedia and database requests)")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )

    tree = DecisionTreeClassifier(max_depth=6, random_state=seed)
    tree.fit(X_train, y_train)
    tree_metrics = _eval_model(tree, X_test, y_test, "decision_tree")

    scaler = StandardScaler().fit(X_train)
    svm = SVC(kernel="rbf", random_state=seed)
    svm.fit(scaler.transform(X_train), y_train)
    svm_metrics = _eval_model(svm, scaler.transform(X_test), y_test, "svm_baseline")

    return {"decision_tree": tree_metrics, "svm_baseline": svm_metrics}
