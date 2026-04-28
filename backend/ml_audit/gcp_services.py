"""
gcp_services.py
Drop this into backend/ml-audit/ to replace your mock services.
Wires EquiLabel to real BigQuery, Vertex AI, Gemini, and Cloud Storage.
"""
from asyncio import base_events
from asyncio import base_events
from asyncio import base_events
from asyncio import base_events
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# Google Cloud imports
from google.cloud import bigquery, storage
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel

# --- CONFIG ---
PROJECT_ID = os.getenv("PROJECT_ID", "equilabel-gsc-26")
LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
BUCKET_NAME = os.getenv("GCS_BUCKET", "equilabel-models--gsc-26")
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\PREETI\equilabel\backend\secrets\key.json"
DATASET_ID = "equilabel_audit"
TABLE_ID = "fairness_reports"

# Initialize clients
bq_client = bigquery.Client(project=PROJECT_ID)
gcs_client = storage.Client(project=PROJECT_ID)
aiplatform.init(project=PROJECT_ID, location=LOCATION)

# Gemini model
gemini_model = GenerativeModel(
    "gemini-2.5-flash",
)


class BigQueryLogger:
    """Logs every audit result to BigQuery for historical tracking."""

    def __init__(self):
        self.table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    def log_audit(self, audit_id: str, model_name: str, metrics: dict) -> bool:
        """Insert a fairness report row into BigQuery."""
        row = {
            "audit_id": audit_id,
            "created_at": datetime.utcnow().isoformat(),
            "model_name": model_name,
            "accuracy": metrics.get("accuracy", 0.0),
            "fairness_score": metrics.get("fairness_score", 0.0),
            "demographic_parity": json.dumps(metrics.get("demographic_parity", {})),
            "equalized_odds": json.dumps(metrics.get("equalized_odds", {})),
            "proxy_alerts": json.dumps(metrics.get("proxy_alerts", [])),
            "feature_attributions": json.dumps(metrics.get("feature_attributions", {})),
            "dataset_size": metrics.get("dataset_size", 0),
            "protected_attribute": metrics.get("protected_attribute", "race")
        }

        errors = bq_client.insert_rows_json(self.table_ref, [row])
        if errors:
            print(f"BigQuery insert errors: {errors}")
            return False
        return True

    def get_audit_history(self, model_name: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Retrieve historical audits for the monitoring dashboard."""
        query = f"""
            SELECT * FROM `{self.table_ref}`
            {"WHERE model_name = @model_name" if model_name else ""}
            ORDER BY created_at DESC
            LIMIT @limit
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("model_name", "STRING", model_name),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ] if model_name else [
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
        )
        df = bq_client.query(query, job_config=job_config).to_dataframe()
        return df.to_dict("records")


class GeminiFairnessAgent:
    """Generates human-readable explanations and mitigation code using Gemini."""

    def explain_metrics(self, metrics: dict, audience: str = "hospital_admin") -> str:
        """Generate a plain-English explanation of bias findings."""
        alerts = metrics.get('proxy_alerts', [])
        if alerts and len(alerts) > 0:
            primary_alert = alerts[0]
            proxy_feature = primary_alert.get('feature', 'None')
            proxy_target = primary_alert.get('correlates_with', 'N/A')
            proxy_corr = primary_alert.get('correlation', 'N/A')
        else:
            proxy_feature, proxy_target, proxy_corr = 'None', 'N/A', 'N/A'

        prompt = f"""
You are EquiLabel, an AI fairness auditor. Explain the following bias audit results 
to a {audience.replace('_', ' ')}. Be specific, empathetic, and actionable. 
Use 3-4 short paragraphs. Highlight the most critical finding first.

AUDIT RESULTS:
- Model Accuracy: {metrics.get('accuracy', 'N/A')}
- Fairness Score: {metrics.get('fairness_score', 'N/A')}/1.0
- Demographic Parity Gap: {metrics.get('demographic_parity', {}).get('disparate_impact_ratio', 'N/A')}
- Most Biased Feature: {metrics.get('feature_attributions', {}).get('top_biased_features', ['N/A'])[0]}
- Proxy Alert: {proxy_feature} correlates with {proxy_target} at r={proxy_corr}

Explain:
1. What the numbers mean in human terms
2. Who is being harmed and how
3. One specific action to fix it
        """.strip()

        try:
            response = gemini_model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 1024, "temperature": 0.4},
            )
            return response.text
        except Exception as e:
            print(f"Gemini explain_metrics error: {e}")
            return f"Could not generate explanation. Error: {str(e)}"

    def generate_mitigation_code(self, metrics: dict) -> str:
        """Generate Python code to fix the detected bias."""

        top_feature = metrics.get('feature_attributions', {}).get('top_biased_features', ['unknown'])[0]
        protected = metrics.get('protected_attribute', 'race')

        prompt = f"""
Generate Python code using fairlearn or sklearn to mitigate bias in an ML model.

CONTEXT:
- The model shows disparate impact on {protected}
- The most biased feature is: {top_feature}
- Fairness score: {metrics.get('fairness_score')}

Provide:
1. A complete, copy-pasteable Python function
2. Use ExponentiatedGradient or CorrelationRemover from fairlearn
3. Include comments explaining each step
4. Return the corrected model and a fairness check

Code:
        """.strip()

        response = gemini_model.generate_content(prompt)
        return response.text

    def answer_question(self, question: str, metrics: dict) -> str:
        """Answer ad-hoc questions about the audit (chat interface)."""

        # Format key metrics in a readable way
        eq_odds = metrics.get('equalized_odds', {})
        dem_par = metrics.get('demographic_parity', {})
        top_features = metrics.get('feature_attributions', {}).get('top_biased_features', [])
        proxy_alerts = metrics.get('proxy_alerts', [])

        prompt = f"""
You are EquiLabel, an expert AI fairness auditor assistant. A hospital administrator is asking about 
their ML model's fairness audit results. Answer their question clearly and helpfully.

Use the specific audit numbers below AND your broader ML fairness expertise to give 
a complete, actionable answer. Do not say "I don't know" — always explain the concept 
and relate it to the specific values in this audit.

AUDIT SUMMARY:
- Model: {metrics.get('model_name', 'Unknown')}
- Accuracy: {metrics.get('accuracy', 'N/A'):.1%}
- Fairness Score: {metrics.get('fairness_score', 'N/A'):.1%}
- Protected Attribute: {metrics.get('protected_attribute', 'N/A')}
- Dataset Size: {metrics.get('dataset_size', 'N/A')} records
- Demographic Parity (Disparate Impact Ratio): {dem_par.get('disparate_impact_ratio', 'N/A')}
- TPR Gap (Equalized Odds): {eq_odds.get('tpr_gap', 'N/A')}
- FPR Gap (Equalized Odds): {eq_odds.get('fpr_gap', 'N/A')}
- Top Biased Features: {', '.join(top_features) if top_features else 'None identified'}
- Proxy Alerts: {len(proxy_alerts)} detected

FULL METRICS JSON (for reference):
{json.dumps(metrics, indent=2)}

USER QUESTION: {question}

Provide a clear, helpful answer in 2-4 short paragraphs. Be specific — reference the actual 
numbers from this audit. Give practical, actionable recommendations where relevant.
        """.strip()

        try:
            response = gemini_model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 1024, "temperature": 0.4},
            )
            return response.text
        except Exception as e:
            print(f"Gemini answer_question error: {e}")
            return f"Could not answer your question. Error: {str(e)}"


class VertexAIPredictor:
    """Calls a deployed Vertex AI endpoint for real-time predictions."""

    def __init__(self, endpoint_id: str):
        self.endpoint = aiplatform.Endpoint(
            f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{endpoint_id}"
        )

    def predict(self, instances: List[Dict]) -> List[float]:
        """Send instances to Vertex AI endpoint. Returns prediction probabilities."""
        response = self.endpoint.predict(instances=instances)
        # XGBoost returns class probabilities; we want the positive class
        return [pred[1] for pred in response.predictions]


class GCSUploader:
    """Handles dataset and model artifact uploads to Cloud Storage."""

    def __init__(self):
        self.bucket = gcs_client.bucket(BUCKET_NAME)

    def upload_dataset(self, local_path: str, audit_id: str) -> str:
        """Upload a CSV to GCS and return the gs:// URI."""
        blob_name = f"audits/{audit_id}/dataset.csv"
        blob = self.bucket.blob(blob_name)
        blob.upload_from_filename(local_path)
        return f"gs://{BUCKET_NAME}/{blob_name}"

    def upload_report(self, audit_id: str, report_json: dict) -> str:
        """Upload a JSON report to GCS."""
        blob_name = f"audits/{audit_id}/report.json"
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(json.dumps(report_json), content_type="application/json")
        return f"gs://{BUCKET_NAME}/{blob_name}"


# --- SINGLETON INSTANCES ---
# Import these in your FastAPI routes
bq_logger = BigQueryLogger()
gemini_agent = GeminiFairnessAgent()
gcs_uploader = GCSUploader()
