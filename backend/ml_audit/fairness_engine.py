"""
fairness_engine.py
Core algorithmic module for EquiLabel.
Computes fairness metrics, detects proxy variables, and generates feature attributions.
"""
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from typing import Dict, List

class FairnessEngine:
    """Computes algorithmic fairness metrics on tabular datasets."""

    def compute_metrics(self, df: pd.DataFrame, protected_attribute: str, target: str) -> Dict:
        """
        Compute comprehensive fairness metrics.

        Args:
            df: DataFrame with features + target + protected attribute
            protected_attribute: Column name of protected attribute (e.g., 'race', 'gender')
            target: Binary target column (0/1)
        """
        # If there's no prediction column, we train a quick RF to simulate model predictions
        # In production, this would come from Vertex AI endpoint
        if 'prediction' not in df.columns:
            df = self._add_predictions(df, target)

        y_true = df[target]
        y_pred = df['prediction']

        # Overall accuracy
        accuracy = accuracy_score(y_true, y_pred)

        # Demographic Parity
        dp = self._demographic_parity(df, protected_attribute, 'prediction')

        # Equalized Odds (TPR and FPR by group)
        eo = self._equalized_odds(df, protected_attribute, target, 'prediction')

        # Fairness score: composite metric
        # 1.0 = perfect fairness, <0.8 = concerning
        fairness_score = self._compute_fairness_score(dp, eo)

        # Feature attributions (what drives bias)
        attributions = self._feature_attributions(df, target, protected_attribute)

        return {
            "accuracy": round(accuracy, 3),
            "fairness_score": round(fairness_score, 2),
            "demographic_parity": dp,
            "equalized_odds": eo,
            "feature_attributions": attributions
        }

    def _add_predictions(self, df: pd.DataFrame, target: str) -> pd.DataFrame:
        """Train a quick model to simulate predictions for demo purposes."""
        df = df.copy()
        feature_cols = [c for c in df.columns if c not in [target, 'patient_id']]

        # Handle categoricals
        X = pd.get_dummies(df[feature_cols], drop_first=True)
        y = df[target]

        model = RandomForestClassifier(n_estimators=50, random_state=42, max_depth=5)
        model.fit(X, y)
        df['prediction'] = model.predict(X)
        return df

    def _demographic_parity(self, df: pd.DataFrame, protected: str, prediction: str) -> Dict:
        """P(Y_hat=1 | A=a) should be equal across groups."""
        groups = df[protected].unique()
        rates = {}

        for g in groups:
            subset = df[df[protected] == g]
            rate = subset[prediction].mean()
            rates[str(g)] = round(float(rate), 3)

        # Disparate Impact Ratio = min(rate) / max(rate)
        min_rate = min(rates.values())
        max_rate = max(rates.values())
        di_ratio = min_rate / max_rate if max_rate > 0 else 1.0

        return {
            "groups": rates,
            "disparate_impact_ratio": round(di_ratio, 3),
            "is_compliant": di_ratio >= 0.8  # EEOC 80% rule
        }

    def _equalized_odds(self, df: pd.DataFrame, protected: str, target: str, prediction: str) -> Dict:
        """TPR and FPR should be equal across groups."""
        groups = df[protected].unique()
        tpr_by_group = {}
        fpr_by_group = {}

        for g in groups:
            subset = df[df[protected] == g]
            if len(subset) < 2:
                continue

            cm = confusion_matrix(subset[target], subset[prediction], labels=[0, 1])
            tn, fp, fn, tp = cm.ravel()

            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

            tpr_by_group[str(g)] = round(float(tpr), 3)
            fpr_by_group[str(g)] = round(float(fpr), 3)

        tpr_values = list(tpr_by_group.values())
        fpr_values = list(fpr_by_group.values())

        return {
            "true_positive_rates": tpr_by_group,
            "false_positive_rates": fpr_by_group,
            "tpr_gap": round(max(tpr_values) - min(tpr_values), 3) if tpr_values else 0,
            "fpr_gap": round(max(fpr_values) - min(fpr_values), 3) if fpr_values else 0
        }

    def _compute_fairness_score(self, dp: Dict, eo: Dict) -> float:
        """Composite score from 0-1."""
        di_score = dp.get("disparate_impact_ratio", 1.0)
        tpr_penalty = 1 - eo.get("tpr_gap", 0)
        fpr_penalty = 1 - eo.get("fpr_gap", 0)

        # Weighted average
        score = (di_score * 0.5) + (tpr_penalty * 0.25) + (fpr_penalty * 0.25)
        return max(0, min(1, score))

    def detect_proxies(self, df: pd.DataFrame, protected_attribute: str, threshold: float = 0.65) -> List[Dict]:
        """
        Detect features that strongly correlate with protected attributes.
        Uses Cramér's V for categorical-categorical and correlation for numeric.
        """
        alerts = []
        protected = df[protected_attribute]

        for col in df.columns:
            if col in [protected_attribute, 'patient_id', 'prediction', 'icu_admitted']:
                continue

            corr = self._compute_correlation(df[col], protected)

            if abs(corr) >= threshold:
                alerts.append({
                    "feature": col,
                    "correlates_with": protected_attribute,
                    "correlation": round(float(corr), 3),
                    "severity": "HIGH" if abs(corr) > 0.8 else "MEDIUM"
                })

        return sorted(alerts, key=lambda x: abs(x["correlation"]), reverse=True)

    def _compute_correlation(self, x: pd.Series, y: pd.Series) -> float:
        """Compute appropriate correlation based on data types."""
        if x.dtype == 'object' and y.dtype == 'object':
            # Cramér's V (simplified)
            return self._cramers_v(x, y)
        elif x.dtype == 'object':
            # Point-biserial approximation
            return self._eta_squared(x, y)
        elif y.dtype == 'object':
            return self._eta_squared(y, x)
        else:
            return x.corr(y)

    def _cramers_v(self, x: pd.Series, y: pd.Series) -> float:
        """Simplified Cramér's V for categorical association."""
        confusion_matrix = pd.crosstab(x, y)
        chi2 = self._chi2_from_crosstab(confusion_matrix)
        n = confusion_matrix.sum().sum()
        phi2 = chi2 / n
        r, k = confusion_matrix.shape
        phi2corr = max(0, phi2 - ((k-1)*(r-1))/(n-1))
        rcorr = r - ((r-1)**2)/(n-1)
        kcorr = k - ((k-1)**2)/(n-1)
        return np.sqrt(phi2corr / min((kcorr-1), (rcorr-1))) if min(kcorr-1, rcorr-1) > 0 else 0

    def _chi2_from_crosstab(self, ct: pd.DataFrame) -> float:
        """Compute chi-squared statistic from crosstab."""
        observed = ct.values
        row_totals = observed.sum(axis=1, keepdims=True)
        col_totals = observed.sum(axis=0, keepdims=True)
        n = observed.sum()
        expected = row_totals @ col_totals / n
        return ((observed - expected)**2 / expected).sum()

    def _eta_squared(self, cat: pd.Series, num: pd.Series) -> float:
        """Correlation ratio for categorical vs numeric."""
        categories = cat.unique()
        overall_mean = num.mean()
        ss_between = sum(len(num[cat == c]) * (num[cat == c].mean() - overall_mean)**2 for c in categories)
        ss_total = ((num - overall_mean)**2).sum()
        return np.sqrt(ss_between / ss_total) if ss_total > 0 else 0

    def _feature_attributions(self, df: pd.DataFrame, target: str, protected: str) -> Dict:
        """Identify which features most drive biased predictions."""
        df = df.copy()
        feature_cols = [c for c in df.columns if c not in [target, 'patient_id', protected]]
        X = pd.get_dummies(df[feature_cols], drop_first=True)
        y = df[target]

        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(X, y)

        # Permutation importance on protected attribute prediction
        # Features that help predict the protected attribute are proxies
        protected_encoded = pd.get_dummies(df[protected], drop_first=True)
        if protected_encoded.shape[1] > 0:
            prot_model = RandomForestClassifier(n_estimators=30, random_state=42)
            prot_model.fit(X, protected_encoded.iloc[:, 0])
            imp = permutation_importance(prot_model, X, protected_encoded.iloc[:, 0], 
                                         n_repeats=5, random_state=42)
            top_idx = np.argsort(imp.importances_mean)[-5:][::-1]
            top_features = [X.columns[i] for i in top_idx if imp.importances_mean[i] > 0.01]
        else:
            top_features = []

        return {
            "top_biased_features": top_features[:3],
            "method": "permutation_importance_on_protected_attribute"
        }