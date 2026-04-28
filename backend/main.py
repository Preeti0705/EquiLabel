"""
main.py
Updated FastAPI backend with real GCP integration.
Drop this into backend/ and update your requirements.txt.
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd
import numpy as np
import json
import uuid
import asyncio
from functools import partial
from typing import Optional
import io

# Import your modules
from ml_audit.fairness_engine import FairnessEngine
from ml_audit.gcp_services import bq_logger, gemini_agent, gcs_uploader

app = FastAPI(title="EquiLabel API", version="1.0.0")

# CORS for Flutter local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store (use Firestore in production)
audit_jobs = {}

# --- PYDANTIC MODELS ---
class ExplainRequest(BaseModel):
    question: str
    audience: Optional[str] = "hospital_admin"

class MitigateRequest(BaseModel):
    strategy: Optional[str] = "reweighting"

# --- CORE ENGINE ---
engine = FairnessEngine()

# --- ROUTES ---
@app.post("/api/v1/audit/upload")
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_name: Optional[str] = "untitled_model",
    protected_attribute: Optional[str] = "race"
):
    """Accept CSV, start async audit, return audit_id."""
    audit_id = f"eq-{uuid.uuid4().hex[:8]}"

    # Read CSV
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

    # Save temporarily (in production, stream to GCS)
    # temp_path = f"/tmp/{audit_id}.csv"
    # df.to_csv(temp_path, index=False)
    # This will use /tmp in Docker/Linux or the standard Temp folder in Windows
    import tempfile
    import os

    temp_dir = tempfile.gettempdir() 
    temp_path = os.path.join(temp_dir, f"{audit_id}.csv")
    df.to_csv(temp_path, index=False)

    # Start background audit
    audit_jobs[audit_id] = {
        "status": "processing",
        "progress": 0,
        "model_name": model_name,
        "protected_attribute": protected_attribute,
        "dataset_size": len(df)
    }

    background_tasks.add_task(run_audit, audit_id, temp_path, model_name, protected_attribute)

    return {"audit_id": audit_id, "status": "processing"}

@app.get("/api/v1/audit/{audit_id}/status")
async def get_status(audit_id: str):
    """Poll this from Flutter every 2 seconds."""
    if audit_id not in audit_jobs:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit_jobs[audit_id]

@app.get("/api/v1/audit/{audit_id}/report")
async def get_report(audit_id: str):
    """Return the full fairness report JSON."""
    if audit_id not in audit_jobs:
        raise HTTPException(status_code=404, detail="Audit not found")

    job = audit_jobs[audit_id]
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail="Audit still processing")

    return job["report"]

@app.post("/api/v1/audit/{audit_id}/explain")
async def explain_audit(audit_id: str, req: ExplainRequest):
    """Gemini-generated explanation of bias findings."""
    if audit_id not in audit_jobs or audit_jobs[audit_id]["status"] != "complete":
        raise HTTPException(status_code=400, detail="Audit not complete yet. Please wait for processing to finish.")

    report = audit_jobs[audit_id]["report"]
    # Run blocking Gemini SDK call in a thread so it doesn't freeze the event loop
    loop = asyncio.get_event_loop()
    explanation = await loop.run_in_executor(
        None, partial(gemini_agent.explain_metrics, report, req.audience)
    )

    return {"explanation": explanation}

@app.post("/api/v1/audit/{audit_id}/chat")
async def chat_about_audit(audit_id: str, req: ExplainRequest):
    """Ad-hoc chat interface for the audit."""
    if audit_id not in audit_jobs or audit_jobs[audit_id]["status"] != "complete":
        raise HTTPException(status_code=400, detail="Audit not complete yet. Please wait for processing to finish.")

    report = audit_jobs[audit_id]["report"]
    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(
        None, partial(gemini_agent.answer_question, req.question, report)
    )

    return {"answer": answer}

@app.post("/api/v1/audit/{audit_id}/mitigate")
async def mitigate_audit(audit_id: str, req: MitigateRequest):
    """Generate mitigation code via Gemini."""
    if audit_id not in audit_jobs or audit_jobs[audit_id]["status"] != "complete":
        raise HTTPException(status_code=400, detail="Audit not complete")

    report = audit_jobs[audit_id]["report"]
    code = gemini_agent.generate_mitigation_code(report)

    return {"mitigation_code": code, "strategy": req.strategy}

@app.get("/api/v1/audits/history")
async def get_history(model_name: Optional[str] = None, limit: int = 50):
    """Fetch historical audits from BigQuery for the monitoring dashboard."""
    history = bq_logger.get_audit_history(model_name=model_name, limit=limit)
    return {"audits": history}

# --- BACKGROUND TASK ---
def run_audit(audit_id: str, csv_path: str, model_name: str, protected_attr: str):
    """The actual audit computation."""
    try:
        df = pd.read_csv(csv_path)

        # Flexible target detection
        possible_targets = ['icu_admitted', 'admitted', 'outcome', 'target', 'label']
        actual_target = None
        for pt in possible_targets:
            if pt in df.columns:
                actual_target = pt
                break
        
        if not actual_target:
            raise ValueError(f"Target column not found. Expected one of: {possible_targets}")

        # Simulate progress steps
        audit_jobs[audit_id]["progress"] = 20

        # Compute fairness metrics
        metrics = engine.compute_metrics(df, protected_attribute=protected_attr, target=actual_target)
        audit_jobs[audit_id]["progress"] = 60

        # Detect proxy variables
        proxies = engine.detect_proxies(df, protected_attr)
        audit_jobs[audit_id]["progress"] = 80

        # Build report
        report = {
            "audit_id": audit_id,
            "model_name": model_name,
            "accuracy": metrics["accuracy"],
            "fairness_score": metrics["fairness_score"],
            "demographic_parity": metrics["demographic_parity"],
            "equalized_odds": metrics["equalized_odds"],
            "proxy_alerts": proxies,
            "feature_attributions": metrics["feature_attributions"],
            "dataset_size": len(df),
            "protected_attribute": protected_attr
        }

        # Upload to GCS (Optional fallback)
        try:
            gcs_uploader.upload_dataset(csv_path, audit_id)
            gcs_uploader.upload_report(audit_id, report)
        except Exception as e:
            print(f"Warning: GCS upload failed: {e}")

        # Log to BigQuery (Optional fallback)
        try:
            bq_logger.log_audit(audit_id, model_name, report)
        except Exception as e:
            print(f"Warning: BigQuery logging failed: {e}")

        # Mark complete
        audit_jobs[audit_id]["status"] = "complete"
        audit_jobs[audit_id]["progress"] = 100
        audit_jobs[audit_id]["report"] = report

    except Exception as e:
        audit_jobs[audit_id]["status"] = "failed"
        audit_jobs[audit_id]["error"] = str(e)
        print(f"Audit {audit_id} failed: {e}")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "equilabel-api"}