---
company: EloGroup
client: Comgás (allocated; Brazil's largest natural-gas distributor)
location: São Paulo, BR
mode: Remote
start: 2021-06
end: 2022-09
titles:
  - Data Scientist Intern
---

Format: see nubank.md.

## Natural-gas demand forecasting: ~R$200M in avoided fines  [ml]

Facts: EDA, sanity checks, seasonality and residual analysis over 24 city-level series (citygates: metering and pressure regulation stations); ADF, KPSS, Granger-causality and Ljung-Box tests; co-implemented a mixed ensemble (LightGBM, SARIMAX, Holt-Winters, intra-daily volume proportion); optimized demand programming with Petrobras; ~R$200M in contractual fines avoided in the first three months; 18 of 24 citygates within the 5% fine threshold.

Variants:
- Helped cut natural-gas contractual fines by roughly R$200M in the first three months by performing EDA, sanity checks and time-series modeling over 24 city-level series for Comgás, enabling an ensemble forecast that kept 18 of 24 citygates within the 5% fine threshold.
- Co-implemented a LightGBM/SARIMAX/Holt-Winters ensemble over 24 city-level gas demand series, validated with ADF, KPSS, Granger and Ljung-Box tests, optimizing demand programming with Petrobras and avoiding ~R$200M in fines in three months.

## Azure ML forecasting pipelines (MLOps)  [ml] [data-eng] [platform]

Facts: end-to-end pipelines in Azure ML orchestrated by Azure Data Factory, migrated from a Databricks-only solution; delta datasets from Azure Data Lake Gen2; Python and Databricks (PySpark) for batch feature engineering, training and scoring; predictions to Azure Blob Storage, post-processed on Databricks, views in Azure Synapse, Power BI dashboards for gas programming analysts; MLflow experiment tracking, model registry, versioning; medallion architecture stages with automated data quality checks and pipeline troubleshooting; Git and Azure DevOps with Databricks Repos.

Variants:
- Increased reliability and observability of forecasting workflows by co-designing end-to-end ML pipelines in Azure ML with MLflow tracking, migrating the Databricks-only solution to a managed setup orchestrated by Azure Data Factory and Azure Data Lake.
- Built Azure ML pipelines from Data Lake to Power BI (Data Factory, Databricks, Synapse) with MLflow model tracking and automated data quality checks in a medallion architecture.

## Streamlit tools: time-series workbench and NLP framework  [ml] [analytics]

Facts: Streamlit app automating a Box-Jenkins-inspired methodology (time-series visualization, model evaluation, sharing results with stakeholders); co-implemented an internal NLP framework in Streamlit with spaCy and NLTK (tokenization, parsing, classification) reused across consulting projects.

Variants:
- Standardized text processing across consulting projects by co-implementing an internal NLP framework in Streamlit with spaCy and NLTK.
- Built a Streamlit app that automated a Box-Jenkins-style forecasting workflow, from visualization to model evaluation, for business stakeholders.

**Technologies and tools:** Python, PySpark, SQL, Spark, Databricks, LightGBM, SARIMAX, Holt-Winters, statsmodels, Streamlit, spaCy, NLTK, MLflow, Azure ML, Azure Data Factory, Azure Data Lake, Azure Synapse, Azure Blob Storage, Power BI, Git, Azure DevOps
