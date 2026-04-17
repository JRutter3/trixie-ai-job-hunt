# Trixie AI Job Hunt: The Sovereign Architect's Chief of Staff

A high-signal, automated lead-scoring system designed to filter recruiter outreach, categorize opportunities, and act as a technical "gatekeeper."

## 🎯 Project Vision
To minimize "recruitment noise" by applying architectural rigor to the job search. The system identifies high-value ("Sovereign") opportunities and automates the initial qualifying interactions, allowing the user to focus only on high-signal leads.

## 🏗 Architectural Overview
This project is built as a **Modular Monolith** designed for stateless execution on **Google Cloud Run Jobs**.

- **Ingest:** EZGmail poller for LinkedIn/Email outreach.
- **Brain:** LLM-based (Claude 4.7) intent classification and scoring.
- **Data:** PostgreSQL (Sovereign leads) + Secret Manager (OAuth tokens).
- **Notify:** GroupMe/Email alerts for Tier 1 leads.


## 📊 Lead Scoring Logic (The "Sovereign" Tiers)
Based on the handwritten technical specifications, leads are categorized by "Signal Strength":

| Tier | Designation | Description | Action |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Sovereign** | High-value direct hires, FinTech, or Architecture roles. | Immediate Notify + Draft Response |
| **Tier 2** | **High Signal** | Reputable agencies or specific tech stack matches (FastAPI/K8s). | Log to DB + Daily Digest |
| **Tier 3** | **General Interest** | Standard recruiter outreach with missing details. | Auto-reply for "JD/Salary" |
| **Tier 4** | **Noise** | Mass-blast data harvesters or mismatched stacks. | Silent Archive |
