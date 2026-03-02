"""
Gemini AI Client
Wraps google-generativeai SDK for data analysis insights.
Uses chunked requests to avoid exceeding API quota limits.
"""
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Delay between API calls (seconds) to stay within rate limits
CHUNK_DELAY = 2


def get_gemini_client():
    """Initialize and return a Gemini generative model client."""
    if GEMINI_API_KEY == "YOUR_API_KEY_HERE" or not GEMINI_API_KEY:
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model
    except Exception as e:
        print(f"Error initializing Gemini: {e}")
        return None


def _trim_summary(table_summary: dict) -> dict:
    """
    Trim a table summary to reduce token count.
    Keeps column names, dtypes, unique counts, and top 3 values only.
    """
    trimmed = {
        "table_name": table_summary["table_name"],
        "rows": table_summary["rows"],
        "columns": table_summary["columns"],
        "column_details": []
    }
    for col in table_summary.get("column_details", []):
        tc = {
            "name": col["name"],
            "dtype": col["dtype"],
            "unique_count": col["unique_count"],
        }
        # Only keep min/max/mean for numeric (skip raw values)
        if "mean" in col:
            tc["min"] = col.get("min")
            tc["max"] = col.get("max")
            tc["mean"] = col.get("mean")
        # Only keep top 3 values instead of 5
        if "top_values" in col:
            top = col["top_values"]
            tc["top_values"] = dict(list(top.items())[:3])
        trimmed["column_details"].append(tc)
    return trimmed


def _parse_response(text: str) -> dict:
    """Parse a Gemini response, handling markdown fences and JSON extraction."""
    text = text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    if text.startswith("json"):
        text = text[4:].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "insights": text,
            "key_findings": [],
            "recommendations": [],
            "kpi_assessment": []
        }


def _call_gemini(model, prompt: str, retries: int = 2) -> str:
    """Call Gemini with retry logic and delays."""
    for attempt in range(retries + 1):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "rate" in err_str or "429" in err_str:
                if attempt < retries:
                    wait_time = CHUNK_DELAY * (attempt + 2)
                    print(f"Rate limited, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
            raise e
    return ""


def analyze(data_summary: list[dict], user_query: str) -> dict:
    """
    Send data context + user query to Gemini using chunked requests.

    Strategy:
    1. If only 1-2 tables, send in a single request.
    2. If 3+ tables, first collect per-table bullet points in chunks,
       then send a final synthesis request with those bullet points.
    """
    model = get_gemini_client()
    if model is None:
        return {
            "error": "Gemini API key not configured. Please set GEMINI_API_KEY in .env file.",
            "insights": "",
            "key_findings": [],
            "recommendations": [],
            "kpi_assessment": []
        }

    # Trim all summaries to reduce tokens
    trimmed = [_trim_summary(s) for s in data_summary]

    try:
        if len(trimmed) <= 2:
            # Small enough to send in one go
            return _single_request(model, trimmed, user_query)
        else:
            # Chunked approach for 3+ tables
            return _chunked_request(model, trimmed, user_query)
    except Exception as e:
        return {
            "error": str(e),
            "insights": "",
            "key_findings": [],
            "recommendations": [],
            "kpi_assessment": []
        }


def _single_request(model, summaries: list[dict], user_query: str) -> dict:
    """Send all data in a single compact request."""
    data_context = json.dumps(summaries, default=str)

    prompt = f"""You are a senior data analyst. Analyze these datasets and answer the question.

DATASETS:
{data_context}

QUESTION: {user_query}

Respond in this JSON format ONLY (no markdown fences):
{{"insights": "paragraph", "key_findings": ["f1","f2","f3"], "recommendations": ["r1","r2","r3"], "kpi_assessment": [{{"kpi": "name", "status": "Leading or Lagging", "detail": "why"}}]}}

Be specific, reference column names and values."""

    text = _call_gemini(model, prompt)
    return _parse_response(text)


def _chunked_request(model, summaries: list[dict], user_query: str) -> dict:
    """
    Break data into per-table chunks, get bullet points for each,
    then synthesize a final combined analysis.
    """
    partial_insights = []

    # Phase 1: Analyze each table individually (small requests)
    for i, table_summary in enumerate(summaries):
        data_context = json.dumps(table_summary, default=str)

        prompt = f"""You are a data analyst. Analyze this single dataset and provide 3-4 brief bullet points relevant to this question.

DATASET:
{data_context}

QUESTION: {user_query}

Respond with ONLY a short bullet list (3-4 points, one line each). No JSON, no headers. Reference column names."""

        try:
            text = _call_gemini(model, prompt)
            partial_insights.append(f"[{table_summary['table_name']}]\n{text.strip()}")
        except Exception as e:
            partial_insights.append(f"[{table_summary['table_name']}] Error: {str(e)}")

        # Delay between chunks to avoid rate limiting
        if i < len(summaries) - 1:
            time.sleep(CHUNK_DELAY)

    # Phase 2: Synthesize all partial insights into final structured response
    combined_notes = "\n\n".join(partial_insights)

    # Build a compact list of table names and key columns for context
    table_overview = ", ".join(
        f"{s['table_name']} ({s['rows']} rows, {s['columns']} cols)"
        for s in summaries
    )

    synthesis_prompt = f"""You are a senior business strategy consultant. 
I analyzed {len(summaries)} datasets: {table_overview}.

Here are the per-table findings:

{combined_notes}

QUESTION: {user_query}

Now synthesize these into a final analysis. Respond in this JSON format ONLY (no markdown fences):
{{"insights": "A detailed paragraph synthesizing all findings.", "key_findings": ["finding1", "finding2", "finding3"], "recommendations": ["recommendation1", "recommendation2", "recommendation3"], "kpi_assessment": [{{"kpi": "KPI name", "status": "Leading or Lagging", "detail": "explanation"}}]}}"""

    time.sleep(CHUNK_DELAY)
    text = _call_gemini(model, synthesis_prompt)
    return _parse_response(text)


def generate_summary(data_summary: list[dict]) -> dict:
    """
    Generate an automatic business summary without a user query.
    Uses the chunked approach to stay within quota.
    """
    return analyze(
        data_summary,
        "Provide a comprehensive business analysis summary. "
        "Identify all KPIs - which are leading and which are lagging. "
        "Explain where the business is underperforming and provide specific, "
        "actionable strategies to improve business outcomes. "
        "Include insights about customer segments, revenue patterns, "
        "and retention risks."
    )
