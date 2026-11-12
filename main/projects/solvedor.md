---
name: SolvedOR
url: github.com/jvitorcosta/or-solver-streamlit
context: Bachelor thesis, Universidade Federal do Amazonas (2023)
---

Facts: educational app for Industrial Engineering students at UFAM teaching Operations Research and Mathematical Programming through Active and Problem-Based Learning; Google OR-Tools as the solver backend (GLOP for linear, SCIP for integer problems); Streamlit UI. In the 2023 thesis the modeling syntax was parsed with Python regex; in student testing 80% rated building a model in the app easy or very easy (thesis article, paper/ in the repo). In October 2026 Vitor rebuilt it: textbook syntax parsed with pyparsing, syntax errors that name the line, a Plotly plot of the real feasible region for two-variable problems (2D only; there was never a 3D view) with the objective direction, English and Portuguese UI, a fix for unbounded problems being reported as infeasible, 170+ tests including headless runs of the whole app, CI on three OSes; live at https://solvedor.streamlit.app. Errors show when the student solves, not while typing.

Variants:
- Built SolvedOR, a Streamlit app (my bachelor thesis) that teaches Operations Research: students write models in textbook notation, OR-Tools solves them, and Plotly draws the feasible region of two-variable problems. Live at solvedor.streamlit.app.

Tags: [side-project] [optimization] [education]
