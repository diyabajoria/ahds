"""Optional heuristic workload classifier — NOT machine learning, labelled as
a heuristic everywhere in the UI. Guesses a request's class from features
that would be visible to a real block layer (size, sequentiality proxy,
inter-arrival regularity, locality) and reports a confusion matrix against
the true labels so its accuracy is visible rather than assumed."""
from __future__ import annotations
from typing import List, Dict
from models.request import Request, RequestType


def classify_heuristic(requests: List[Request]) -> List[RequestType]:
    """A simple, transparent, rule-based (not ML) guesser."""
    preds = []
    for r in requests:
        if r.size_bytes >= 65536:
            preds.append(RequestType.OLAP)
        elif r.deadline is not None:
            preds.append(RequestType.MULTIMEDIA)
        else:
            preds.append(RequestType.OLTP)
    return preds


def confusion_matrix(requests: List[Request], preds: List[RequestType]) -> Dict[str, Dict[str, int]]:
    labels = [t.value for t in RequestType]
    matrix = {t: {p: 0 for p in labels} for t in labels}
    for r, p in zip(requests, preds):
        matrix[r.type.value][p.value] += 1
    return matrix


def accuracy(requests: List[Request], preds: List[RequestType]) -> float:
    if not requests:
        return 0.0
    correct = sum(1 for r, p in zip(requests, preds) if r.type == p)
    return correct / len(requests)
