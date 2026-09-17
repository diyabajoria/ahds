"""FastAPI layer. Every response echoes the seed and resolved config.
Validation errors are 422 with a readable message; nothing here should ever
500 on bad user input (see docs section 10 / the test suite for the full
list of cases handled)."""
from __future__ import annotations
import io
import uuid
import csv as csv_mod
from collections import OrderedDict
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import ValidationError

from models.simulation import (
    SimulationConfig, CompareRequest, ExperimentRequest, SchedulerName, Direction,
)
from models.request import Request as SimRequest, RequestType, Operation
from simulation.orchestrator import run_one
from simulation.workload_builder import build_workload
from simulation.admission import check_admission, effective_bandwidth_bytes_per_ms
from simulation.classifier_ml import train_and_evaluate
from simulation.degradation import compute_lead_time_before_degradation
from experiments.runner import run_experiment
from experiments.export import requests_to_csv, result_to_json
import presets as presets_module

app = FastAPI(title="Adaptive Hybrid Disk Scheduling Simulator", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

MAX_RESULTS = 50
_results: "OrderedDict[str, dict]" = OrderedDict()


def _store_result(run_id: str, payload: dict):
    _results[run_id] = payload
    _results.move_to_end(run_id)
    while len(_results) > MAX_RESULTS:
        _results.popitem(last=False)


def _downsample_timeline(timeline, target_points: int = 2000):
    n = len(timeline)
    if n <= target_points:
        return [{"time": e.time, "head": e.head, "request_id": e.request_id, "event_type": e.event_type}
                for e in timeline]
    stride = max(1, n // target_points)
    return [{"time": e.time, "head": e.head, "request_id": e.request_id, "event_type": e.event_type}
            for e in timeline[::stride]]


@app.exception_handler(ValidationError)
async def pydantic_validation_handler(request, exc: ValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/schedulers")
def schedulers():
    return {"schedulers": [s.value for s in SchedulerName]}


@app.get("/api/presets")
def presets():
    return {"presets": presets_module.list_presets()}


@app.post("/api/workload/generate")
def generate_workload(cfg: SimulationConfig):
    try:
        requests, stream_periods = build_workload(cfg.workload, cfg.disk)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not requests:
        raise HTTPException(status_code=422, detail="generated workload is empty — "
                             "increase stream/request counts")
    return {
        "seed": cfg.workload.seed,
        "count": len(requests),
        "stream_periods": stream_periods,
        "sample": [r.to_dict() for r in requests[:50]],
    }


def _run_and_store(cfg: SimulationConfig) -> dict:
    engine_result, metrics, scheduler = run_one(cfg)
    run_id = str(uuid.uuid4())
    payload = {
        "run_id": run_id,
        "config": cfg.model_dump(),
        "seed": cfg.workload.seed,
        "metrics": metrics,
        "requests": engine_result.requests,
        "timeline": engine_result.timeline,
    }
    _store_result(run_id, payload)
    return payload


@app.post("/api/simulate")
def simulate(cfg: SimulationConfig):
    if cfg.workload.multimedia.n_streams == 0 and cfg.workload.oltp.n_requests == 0 \
            and cfg.workload.olap.n_scans == 0:
        raise HTTPException(status_code=422, detail="empty workload: at least one of "
                             "multimedia streams, OLTP requests, or OLAP scans must be > 0")
    try:
        payload = _run_and_store(cfg)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    timeline_sample = _downsample_timeline(payload["timeline"])
    return {
        "run_id": payload["run_id"],
        "config": payload["config"],
        "seed": payload["seed"],
        "metrics": payload["metrics"],
        "timeline_sample": timeline_sample,
        "requests_page": [r.to_dict() for r in payload["requests"][:100]],
        "total_requests": len(payload["requests"]),
    }


@app.post("/api/compare")
def compare(req: CompareRequest):
    requests, stream_periods = build_workload(req.workload, req.disk)
    results = []
    for sched_name in req.schedulers:
        cfg = SimulationConfig(
            scheduler=sched_name, disk=req.disk, workload=req.workload,
            hybrid=req.hybrid, direction=req.direction,
        )
        _, metrics, _ = run_one(cfg, requests=requests, stream_periods=stream_periods)
        results.append({"scheduler": sched_name.value, "metrics": metrics})
    return {"seed": req.workload.seed, "results": results}


@app.post("/api/admission/check")
def admission_check(cfg: SimulationConfig, new_bitrate_bytes_per_s: float,
                     reserved_bitrates_bytes_per_s: Optional[List[float]] = None):
    reserved = reserved_bitrates_bytes_per_s or []
    avg_bytes = cfg.workload.multimedia.request_size_bytes
    result = check_admission(
        cfg.disk, avg_bytes, cfg.hybrid.rt_max, reserved, new_bitrate_bytes_per_s,
    )
    return result.__dict__


@app.post("/api/experiment/run")
def experiment_run(req: ExperimentRequest):
    try:
        return run_experiment(req)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/classifier/train")
def classifier_train(cfg: SimulationConfig):
    """Trains the decision-tree workload classifier (+ SVM baseline) on a
    freshly generated workload from `cfg.workload`, and returns
    precision/recall/F1/confusion-matrix for both — Objective 1 /
    docs/project_review.md section 10."""
    requests, _ = build_workload(cfg.workload, cfg.disk)
    try:
        results = train_and_evaluate(requests, seed=cfg.workload.seed)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "seed": cfg.workload.seed,
        "n_requests": len(requests),
        "models": {name: {
            "precision": m.precision, "recall": m.recall, "f1": m.f1,
            "confusion_matrix": m.confusion_matrix,
            "feature_importances": m.feature_importances,
        } for name, m in results.items()},
    }


@app.post("/api/experiment/degradation")
def experiment_degradation(cfg: SimulationConfig, baseline_schedulers: List[SchedulerName],
                            load_start: float = 20.0, load_end: float = 100.0, load_step: float = 10.0):
    """Lead-time-before-degradation — Expected Outcome metric from
    docs/project_review.md section 10."""
    try:
        result = compute_lead_time_before_degradation(
            cfg, baseline_schedulers, load_start=load_start, load_end=load_end, load_step=load_step,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "points": [p.__dict__ for p in result.points],
        "lead_time_load_pct": result.lead_time_load_pct,
        "note": result.note,
    }


@app.post("/api/trace/upload")
async def trace_upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="only .csv trace files are accepted")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=422, detail="trace file too large (10MB limit)")
    try:
        text = raw.decode("utf-8")
        reader = csv_mod.DictReader(io.StringIO(text))
        required = {"timestamp", "cylinder", "size", "operation"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise HTTPException(status_code=422, detail=f"CSV must contain columns: {sorted(required)}")
        requests = []
        for i, row in enumerate(reader):
            requests.append(SimRequest(
                id=i,
                type=RequestType(row.get("type", "OLTP")),
                operation=Operation(row["operation"].upper()),
                arrival_time=float(row["timestamp"]),
                cylinder=int(row["cylinder"]),
                size_bytes=int(row["size"]),
                deadline=float(row["deadline"]) if row.get("deadline") else None,
                stream_id=row.get("stream_id") or None,
            ))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"malformed or wrong-schema CSV: {e}")
    return {"count": len(requests), "sample": [r.to_dict() for r in requests[:20]]}


@app.get("/api/results/{run_id}")
def get_result(run_id: str):
    if run_id not in _results:
        raise HTTPException(status_code=404, detail="run not found (evicted or never existed)")
    payload = _results[run_id]
    return {
        "run_id": run_id, "config": payload["config"], "seed": payload["seed"],
        "metrics": payload["metrics"],
        "total_requests": len(payload["requests"]),
    }


@app.get("/api/results/{run_id}/csv")
def get_result_csv(run_id: str):
    if run_id not in _results:
        raise HTTPException(status_code=404, detail="run not found")
    csv_text = requests_to_csv(_results[run_id]["requests"])
    return PlainTextResponse(csv_text, media_type="text/csv")


@app.get("/api/results/{run_id}/json")
def get_result_json(run_id: str):
    if run_id not in _results:
        raise HTTPException(status_code=404, detail="run not found")
    payload = _results[run_id]
    return JSONResponse(content=__import__("json").loads(
        result_to_json(payload["metrics"], payload["requests"])
    ))
