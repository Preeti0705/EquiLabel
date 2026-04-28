"""
train_and_deploy.py
Train a biased XGBoost model on synthetic MIMIC data, upload to GCS,
and register in Vertex AI Model Registry.
Run this AFTER generating mimic_triage_synthetic.csv
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
import os

# --- 1. LOAD DATA ---
df = pd.read_csv('demo-data\mimic_triage_synthetic.csv')
print(f"Loaded {len(df)} rows")

# --- 2. FEATURE ENGINEERING ---
df_model = df.copy()

# Encode categoricals
le_gender = LabelEncoder()
df_model['gender_enc'] = le_gender.fit_transform(df_model['gender'])

le_race = LabelEncoder()
df_model['race_enc'] = le_race.fit_transform(df_model['race'])

le_insurance = LabelEncoder()
df_model['insurance_enc'] = le_insurance.fit_transform(df_model['insurance_type'])

# Features (NOTE: We include race and insurance so the model LEARNS the bias.
# In production you'd exclude them, but this simulates a flawed real-world model.)
features = ['age', 'gender_enc', 'race_enc', 'insurance_enc', 
            'zip_median_income', 'prior_visits', 'vital_score']
X = df_model[features]
y = df_model['icu_admitted']

# --- 3. TRAIN ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=4,
    learning_rate=0.1,
    subsample=0.8,
    random_state=42,
    eval_metric='logloss'
)
model.fit(X_train, y_train)

# --- 4. EVALUATE (show it learned the bias) ---
from sklearn.metrics import accuracy_score
y_pred = model.predict(X_test)
print(f"\nModel Accuracy: {accuracy_score(y_test, y_pred):.3f}")

# Check bias in predictions
test_df = df_model.iloc[X_test.index].copy()
test_df['pred'] = y_pred
print("\n--- PREDICTION BIAS BY RACE ---")
print(test_df.groupby('race')['pred'].mean().round(3))
print("\n--- PREDICTION BIAS BY GENDER ---")
print(test_df.groupby('gender')['pred'].mean().round(3))

# --- 5. SAVE MODEL ---
os.makedirs('model_artifacts', exist_ok=True)
joblib.dump(model, 'model_artifacts/icu_triage_model.pkl')
joblib.dump(le_gender, 'model_artifacts/le_gender.pkl')
joblib.dump(le_race, 'model_artifacts/le_race.pkl')
joblib.dump(le_insurance, 'model_artifacts/le_insurance.pkl')
print("\nModel saved to model_artifacts/")

# --- 6. UPLOAD TO GCS & REGISTER (run these commands after setting up GCP) ---
print("""
\n=== NEXT STEPS ===
1. Upload to GCS:
   gsutil cp -r model_artifacts/ gs://your-bucket-name/equilabel-models/

2. Register in Vertex AI:
   gcloud ai models upload \
     --region=us-central1 \
     --display-name=icu-triage-biased \
     --artifact-uri=gs://your-bucket-name/equilabel-models/ \
     --container-image-uri=us-docker.pkg.dev/vertex-ai/prediction/xgboost-cpu.1-7:latest

3. Deploy endpoint:
   gcloud ai endpoints deploy-model ENDPOINT_ID \
     --region=us-central1 \
     --model=MODEL_ID \
     --display-name=icu-triage-prod
""")
