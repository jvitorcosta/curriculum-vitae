---
company: Qubika
client: Coastal Community Bank (allocated)
location: Remote
mode: Remote, part-time contract
start: 2026-02
end: 2026-07
titles:
  - Senior AI/ML Engineer
level: Senior
---

Format: see nubank.md.

## LightGBM fraud model cutting false positives  [ml] [platform]

Facts: productionized a single LightGBM fraud detection model aimed at false positives in transaction monitoring; 24-month backtest; transaction-monitoring alert volume −99.2% (12.9M → 98.5K); analyst-facing precision 1.29% → 76.4%; average analyst load ~538K alerts/month at ~78 alerts per confirmed fraud → ~4.1K alerts/month at ~1.3 alerts per confirmed fraud; 131× less review burden; 60× efficiency gain; still surfaces 45% of confirmed fraud.

Variants:
- Productionized a LightGBM fraud detection model that, on a 24-month backtest, cut transaction-monitoring alert volume by 99.2% (12.9M → 98.5K) and lifted analyst-facing precision from 1.29% to 76.4%, a 131× reduction in review burden while still surfacing 45% of confirmed fraud.
- Took analyst load from ~538K alerts/month at ~78 alerts per confirmed fraud to ~4.1K alerts/month at ~1.3 alerts per confirmed fraud with a LightGBM model targeting false positives, a 60× efficiency gain.
- Shipped a LightGBM fraud model that cut false-positive alert volume by 99% and raised precision from 1% to 76%.

## Databricks platform behind the model  [platform] [data-eng] [ml]

Facts: Delta Live Tables pipeline materializing segment-specific feature tables in Unity Catalog; Databricks Asset Bundle orchestrating training, scoring and promotion as version-controlled multi-task jobs; experiments tracked in MLflow; approved models served from the Unity Catalog Model Registry across environments.

Variants:
- Designed and shipped the end-to-end Databricks platform behind the model: a Delta Live Tables pipeline materializing segment-specific feature tables in Unity Catalog, and a Databricks Asset Bundle orchestrating training, scoring and promotion as version-controlled jobs, with MLflow tracking and the Unity Catalog Model Registry across environments.
- Built the MLOps platform for the fraud models with Delta Live Tables, Databricks Asset Bundles, MLflow and Unity Catalog.

## LLM explainability for fraud alerts  [ai] [llm] [ml]

Facts: SHAP attributions per alert; per-segment alert batches; Databricks-hosted foundation model via Mosaic AI Model Serving with structured prompts; two narratives per case (customer context, transaction context); plain-language rationale for analysts; faster case triage.

Variants:
- Built an explainability pipeline that turns each fraud alert into a reviewer-ready rationale by computing SHAP attributions and calling a Databricks-hosted foundation model through Mosaic AI Model Serving with structured prompts, producing customer- and transaction-context narratives that speed up case triage.
- Combined SHAP and an LLM to explain every fraud alert in plain language for analysts.

**Technologies and tools:** Python, SQL, PySpark, Spark, Databricks (Delta Live Tables, Asset Bundles, Unity Catalog, Mosaic AI Model Serving), MLflow, XGBoost, LightGBM, SHAP, GitHub Actions, Azure, Claude, Cursor
