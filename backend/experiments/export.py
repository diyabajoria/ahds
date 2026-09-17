"""CSV/JSON export of a stored run's request table and metrics."""
from __future__ import annotations
import csv
import io
import json
from typing import List
from models.request import Request


def requests_to_csv(requests: List[Request]) -> str:
    if not requests:
        return ""
    buf = io.StringIO()
    fieldnames = list(requests[0].to_dict().keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for r in requests:
        writer.writerow(r.to_dict())
    return buf.getvalue()


def result_to_json(metrics: dict, requests: List[Request]) -> str:
    return json.dumps({
        "metrics": metrics,
        "requests": [r.to_dict() for r in requests],
    }, indent=2, default=str)
