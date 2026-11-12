---
title: My resume, as code
summary: One master record of my career in Markdown, a small CLI that turns it into tailored PDF and Word resumes, and a strict rule that nothing gets invented.
role: Personal project, 2026
pdf: /Vitor_Pinheiro_Resume.pdf
status: approved
---

## The problem

I had about twenty versions of my resume in Google Docs, each tailored to a different job, each a little out of date in its own way. Tailoring a resume for a new posting meant rewriting bullets by hand, and the versions slowly drifted apart until they contradicted each other.

## What I built

A repository where my whole career lives as plain Markdown: every role, every accomplishment with a few approved phrasings, skills, education and side projects. A small Python CLI does the mechanical work. It creates a folder per application, builds clean single-column PDF and Word files through pandoc and Typst, and keeps a tracker of where each application stands.

I tailor each resume with Claude, under one rule written into the repo: every claim must trace back to the master record. Rewording and reordering are fine; new numbers, tools or titles are not. When a posting asks for something I haven't done, it gets listed as a gap instead of filled in.

Before building it, I went through every place my old resumes disagreed and settled each fact one by one, so the master record is the version I can stand behind in an interview.

## Result

Tailoring a resume now starts from one trusted record instead of a pile of old copies. This website is built from the same record, so it never goes stale. Personal data, like my phone number and the companies I apply to, stays out of the repository.

**Stack:** Python, uv, pandoc, Typst, pytest, Claude
