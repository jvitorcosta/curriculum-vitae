---
company: Nubank
team: Global Lending Credit Infra (Lending BU)
location: São Paulo, BR
mode: Hybrid
start: 2022-09
end: 2026-07
titles:
  - Software Engineer (Machine Learning)
official_titles: Machine Learning Engineer (Internship) → Junior Machine Learning Engineer → Machine Learning Engineer, later renamed Software Engineer in a company-wide change (same role)
levels: Intern (from Sep 2022) → Jr Engineer → Engineer
---

Format: each `##` is one accomplishment. **Facts** are what a resume may claim. **Variants** are approved phrasings to pick from. Tags: [ai] [ml] [data-eng] [platform] [analytics] [llm]. Internal notes about these facts live outside this repo.

## Slack AI support assistant  (Engineer) [ai] [llm] [platform]

Facts: Vitor built it. Retrieval-augmented (RAG), multi-agent: a general assistant connected to individual agents, one per internal Lending data tool; Vitor built the general assistant and several of the tool-specific agents, and worked on the shared repository so other developers could add new content and new agents to the general assistant through a standard workflow. Knowledge sources: repository definitions of metrics and segments (the business-concept catalogs), standard definitions from Confluence, the dashboard framework's GitHub code, examples and docs, and history from the support Slack channels (common questions and doubts). Slack bot built with the Slack SDK calling a FastAPI service; Python, LangChain, LangGraph, OpenAI, Slack SDK; runs as a FastAPI service deployed with Docker/Kubernetes; resolves 80% of support tickets autonomously, ~10 → ~2 per week; freed engineering time for infra and features.

Variants:
- Built a Slack AI assistant using Python, LangChain, LangGraph and OpenAI over the framework's codebase, documentation and Slack channel history, deployed in production with Docker/Kubernetes, autonomously resolving 80% of support tickets (10 → 2/week) and unlocking engineering hours for infrastructure and feature improvements.
- Built an AI support agent for the internal dashboard framework's Slack help channel with LangChain, LangGraph and the Slack SDK over the framework's GitHub code, examples and docs, cutting human-handled tickets from ~10/week to ~2/week so engineers could focus on complex issues.
- Built a production LangGraph agent that answers internal support questions from code and docs, resolving 80% of tickets without a human.
- Built a RAG-based multi-agent Slack assistant for internal Lending data tools: a general assistant connected to tool-specific agents over metric and segment definitions, Confluence standards and support-channel history, with a shared repository workflow so other developers could add content and agents; Python, LangChain, LangGraph and OpenAI on FastAPI/Kubernetes, resolving 80% of support tickets (10 → 2/week).

## Databricks Genie proof of concept  (Engineer) [ai] [llm] [analytics]

Facts: evaluated Databricks Genie as a self-service analytics assistant for the Lending BU; POC with business users; prompted, tuned and tested; defined business concepts, instructions and field-level metadata over core customer and loan datasets; handled 3 of 5 test scenarios; documented maturity, ETL and documentation gaps that informed adoption strategy.

Variants:
- Evaluated Databricks Genie as a self-service analytics assistant for the Lending Business Unit through a proof of concept with business users, handling 3 of 5 test scenarios and documenting maturity gaps that informed the adoption strategy.
- Prompted, tuned and evaluated Databricks Genie over core customer and loan datasets, defining business concepts and field-level metadata so it could answer recurring business questions in natural language, and surfaced the ETL and documentation gaps to fix before scaling it.

## Lending NPV framework: Scala → Python  (Mid) [ml] [data-eng]

Facts: simulations across 50+ product lines; co-developed the migration of the Lending NPV (valuation/evaluation) framework from Scala to Python/PySpark; simulates loan performance over time to assess credit decision profitability; supports distributed (PySpark) and single-node runs; unified NPV logic across Python lending models and services (loan eligibility, real-time loan valuation); removed duplicate implementations; built PySpark processing pipelines and automated business sanity checks.

Variants:
- Translated the Lending NPV framework from Scala to Python/PySpark, enabling unified profitability analysis across real-time credit models and services with both distributed and single-node simulations of loan performance and decision economics.
- Standardized the Lending NPV framework by migrating it from Scala to Python, unifying evaluation logic across Python-based lending models (loan eligibility and real-time valuation) and eliminating duplicate implementations.

## Personal-loan offer randomization experiments  (Mid) [ml] [data-eng]

Facts: co-designed and implemented experimentation ("reshuffle") logic in Scala/Spark; randomized offer parameters (number of installments, maximum principal, interest rate) on customer subsamples; reduces survivorship bias in unsecured-lending models; cleaner training data for future credit policy and portfolio decisions; 20%+ cleaner training data.

Variants:
- Generated cleaner, less biased training data for personal-loan models by co-designing Scala/Spark experimentation logic that randomized offer parameters on customer subsamples, reducing survivorship bias and improving future credit policy decisions.
- Designed and implemented randomized-offer experiments for personal loans in Spark/Scala (installments, maximum principal, interest rates) to mitigate survivorship bias and generate cleaner training data for credit policy and portfolio optimization.

## Lending ETL optimization: −34 hours landing time  (Engineer) [data-eng]

Facts: critical Lending core policy datasets; reordered ETL execution, pushed filters earlier in the Scala/Spark DAG, time-based partitioning, partition tuning, removed unnecessary Spark actions; landing time cut by 34 hours; model feature freshness improved by 2 days; fresher loan-parameter features for real-time models that approve or decline loan requests.

Variants:
- Reduced landing time for critical Lending core policy datasets by 34 hours by reordering ETL execution, pushing filters earlier in the Scala/Spark DAG and applying time-based partitioning, improving data freshness for real-time credit models.
- Optimized critical Lending datasets in the company ETL with Scala and Spark (execution reordering, filter pushdown, time-based partitioning), cutting landing time by 34 hours for the features real-time models use to approve or decline loans.

## Low-code dashboard framework (Streamlit)  (Jr/Intern → Engineer) [analytics] [platform]

Facts: co-developed an internal low-code dashboard framework for business analysts; Python/Streamlit; Python package with APIs for plots, filters and aggregations designed to feel like Databricks visualizations; boto3 (aws-wrangler) loading from AWS S3 with SQLite caching; python-pptx exports to slide decks; CLI setup so analysts develop locally and publish via GitHub to an internal site; ~2-day manual reporting → weekly task under an hour; adoption grew from Lending to 19+ business units; several teams replaced Looker; ~1 USD/day infra cost; the framework was deployed with Docker and Kubernetes on AWS. Also provided async and on-call support for the Lending squad's horizontal tools.

Variants:
- Turned a ~2-day manual reporting process into a weekly task of under an hour by co-developing an internal low-code dashboard tool in Python/Streamlit with reusable APIs for plots, filters and aggregations, S3 data loading, SQLite caching, CLI setup and python-pptx exports, driving adoption from Lending to 19+ business units and letting several teams replace Looker at ~1 USD/day in infra costs.
- Designed simple APIs for plots, filters and aggregations that made dashboards as easy as Databricks' native visualizations, driving adoption to 19+ business units and replacing Looker for several teams at roughly 1 USD/day.
- Built python-pptx exports and CLI automations so analysts could develop dashboards locally and publish them with a repeatable workflow.

## Observability and CI/CD  [platform]

Facts: implemented observability frameworks; optimized CI/CD pipelines with GitHub Actions.

Variants:
- Implemented observability for the team's ML services and optimized CI/CD pipelines with GitHub Actions.

## Scala data transformation framework  (Engineer) [data-eng] [platform]

Facts: co-developed a Scala data transformation framework for Global Lending with segment, metric and aggregation catalogs and a shared Scala API; centralized business definitions so users could add and reuse standardized metrics; automated deployment of the shared .jar libraries to Databricks clusters via GitHub Actions.

Variants:
- Co-developed a Scala data transformation framework with segment, metric and aggregation catalogs and a shared API, centralizing Lending business definitions, and automated .jar deployment to Databricks clusters with GitHub Actions so every user stayed on the latest release.

## Data governance initiatives  (Engineer) [data-eng] [platform]

Facts: led Lending data governance initiatives: Lending subdomain migration, SCR monitoring infrastructure setup, credit metrics catalog consolidation; enabled 100% team migration to the new infrastructure.

Variants:
- Led data governance initiatives for Lending, including the subdomain migration, SCR monitoring infrastructure and credit metrics catalog consolidation, moving 100% of the team onto the new infrastructure.

## Monitoring infrastructure support  (Engineer) [platform]

Facts: provided 24/7 monitoring infrastructure support; onboarded multiple business units; consistent platform uptime with zero critical incidents.

Variants:
- Provided 24/7 support for the monitoring infrastructure, onboarding multiple business units with zero critical incidents.

## Risk-model feature engineering  (Engineer) [ml]

Facts: engineered critical features for risk models; improved model performance through systematic feature importance analysis and domain-driven transformations.

Variants:
- Engineered critical features for credit risk models, improving performance through systematic feature-importance analysis and domain-driven transformations.

## Dashboard framework and weekly KPI monitoring  (Engineer) [analytics] [platform]

Facts: built analytics abstractions (filters, aggregations, re-aggregated monitorings) for the internal low-code dashboard framework, cutting execution time from ~20 minutes to ~5 seconds; created a weekly KPI monitoring routine on the framework and an internal data tool, standardizing metrics and segments across credit programs, with 12 business units automating their monitoring on it (19+ BUs use the dashboards overall). Time saved on reporting: ~2 days → under an hour weekly.

Variants:
- Built analytics abstractions (filters, aggregations, re-aggregated monitorings) for an internal low-code dashboard framework, cutting execution time from ~20 minutes to ~5 seconds.
- Created a weekly KPI monitoring routine standardizing metrics and segments across credit programs; 12 business units automated their monitoring on the dashboard framework.

## No-code dashboard builder and data APIs  (Engineer) [analytics] [platform]

Facts: designed APIs for operations over datasets and pre-aggregated monitoring data, letting non-technical users build dashboards without code via a no-code dashboard builder MVP.

Variants:
- Designed APIs over datasets and pre-aggregated monitoring data that let non-technical users build dashboards without code in a no-code dashboard builder MVP.

## Data validation pipelines  (Engineer) [data-eng]

Facts: implemented data validation and monitoring pipelines ensuring data reliability across lending systems.

Variants:
- Implemented data validation and monitoring pipelines that kept lending data reliable across systems.

## Intern-era work  (Intern, from Sep 2022) [ml] [analytics]

Facts: supported development of ML models for credit risk assessment and loan performance prediction; exploratory data analysis on lending datasets to inform business decisions; technical documentation and playbooks for ML workflows.

Variants:
- Supported credit-risk and loan-performance model development, ran EDA on lending datasets, and wrote documentation and playbooks for ML workflows.

**Technologies and tools:** Python, Scala, SQL, PySpark, Spark, Databricks, Streamlit, SQLite, python-pptx, boto3 (aws-wrangler), LangChain, LangGraph, OpenAI, Slack SDK, Docker, Kubernetes, MLflow, GitHub Actions, AWS S3, Cursor, GitHub Copilot
