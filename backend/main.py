"""
Project Data Analyst — FastAPI Backend
Serves the frontend and provides API endpoints for data processing,
relationship analysis, dashboard aggregation, and AI insights.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import pandas as pd
import uuid
import os
import traceback
from pathlib import Path

from backend.services.preprocessing import clean_dataframe, dataframe_to_summary
from backend.services.relationships import detect_relationships
from backend.services.dashboard import compute_dashboard
from backend.services.gemini_client import analyze, generate_summary

# ─── App Setup ────────────────────────────────────────────────
app = FastAPI(title="Project Data Analyst", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── In-memory session store ─────────────────────────────────
# key: session_id, value: { "dataframes": {name: df}, "summaries": [...], "reports": [...] }
sessions: dict = {}

# ─── Directories ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
ERROR_LOG = BASE_DIR / "error_logs.txt"


def log_error(context: str, error: Exception):
    """Append error details to error_logs.txt in the project root."""
    try:
        with open(ERROR_LOG, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Context: {context}\n")
            f.write(f"Error: {error}\n")
            f.write(traceback.format_exc())
            f.write(f"\n{'='*60}\n")
    except Exception:
        pass


# ─── API Endpoints ────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running!"}


@app.post("/upload-and-preprocess")
async def upload_and_preprocess(files: List[UploadFile] = File(...)):
    """
    Step 1: Accept CSV files, clean them, store in session.
    Returns a session_id and cleaning reports.
    """
    try:
        session_id = str(uuid.uuid4())[:8]
        dataframes = {}
        reports = []
        summaries = []

        for file in files:
            if not file.filename.endswith('.csv'):
                raise HTTPException(status_code=400, detail=f"'{file.filename}' is not a CSV file.")

            content = await file.read()
            df = pd.read_csv(pd.io.common.BytesIO(content))

            # Clean the data
            table_name = file.filename.replace('.csv', '')
            cleaned_df, report = clean_dataframe(df, file.filename)
            dataframes[table_name] = cleaned_df
            reports.append(report)
            summaries.append(dataframe_to_summary(cleaned_df, table_name))

        sessions[session_id] = {
            "dataframes": dataframes,
            "summaries": summaries,
            "reports": reports,
        }

        return {
            "session_id": session_id,
            "files_processed": len(files),
            "reports": reports,
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("upload-and-preprocess", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze-relationships")
async def analyze_relationships(session_id: str = Query(...)):
    """
    Step 2: Detect relationships between tables in the session.
    """
    try:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found. Please upload files first.")

        relationships = detect_relationships(session["dataframes"])
        session["relationships"] = relationships

        return {
            "session_id": session_id,
            "relationships": relationships,
            "total_relationships": len(relationships),
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("analyze-relationships", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard-data")
async def dashboard_data(
    session_id: str = Query(...),
    filters: Optional[str] = Query(None)
):
    """
    Step 3: Return aggregated dashboard data (KPIs + charts).
    Accepts optional 'filters' JSON string: {"Region": "West", "Category": "Office Supplies"}
    """
    try:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found. Please upload files first.")

        # Parse filters if provided
        parsed_filters = {}
        if filters:
            import json
            try:
                parsed_filters = json.loads(filters)
            except Exception:
                pass  # Ignore invalid JSON

        dashboard = compute_dashboard(session["dataframes"], filters=parsed_filters)
        return {
            "session_id": session_id,
            **dashboard,
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("dashboard-data", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-insights")
async def generate_insights(
    session_id: str = Query(...),
    query: Optional[str] = Query(None),
):
    """
    Step 4: Use Gemini AI to analyze data and generate insights.
    If no query is provided, generates an automatic business summary.
    """
    try:
        session = sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found. Please upload files first.")

        summaries = session["summaries"]

        if query:
            result = analyze(summaries, query)
        else:
            result = generate_summary(summaries)

        return {
            "session_id": session_id,
            **result,
        }

    except HTTPException:
        raise
    except Exception as e:
        log_error("generate-insights", e)
        raise HTTPException(status_code=500, detail=str(e))


# ─── Static Files & Frontend ─────────────────────────────────
# Mount static files (CSS, JS)
app.mount("/css", StaticFiles(directory=str(PUBLIC_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(PUBLIC_DIR / "js")), name="js")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend HTML."""
    return FileResponse(str(PUBLIC_DIR / "index.html"))
