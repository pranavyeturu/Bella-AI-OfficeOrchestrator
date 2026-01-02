# Bella • Office Orchestrator 🤖📁

A natural-language driven AI assistant that turns plain-English requests into fully-automated business workflows—handling everything from Slack notifications and GitHub deployments to database refreshes and ticket triage.

---

## Key Features

| Category | What Bella Automates |
| -------- | -------------------- |
| **Collaboration & Scheduling** | Find common free slots, create calendar events, post confirmations |
| **People-Ops** | End-to-end onboarding / off-boarding with account provisioning & token revocation |
| **Dev Ops / CI • CD** | One-click image builds, Kubernetes roll-outs, safe rollbacks |
| **Data Engineering** | Hourly API pulls, parquet ⇢ S3, dependency-drift alerts, CSV exports |
| **Support & IT** | Ticket auto-assignment, urgent-complaint routing, daily office summaries |
| **Team Productivity** | Chat noise digests, task-log reminders, PR reviewer round-robin |

---

## Twelve Built-in Workflows  :

1. **Find Common Free Slot & Schedule Meeting** – zero e-mail ping-pong; timezone math handled for you.  
2. **Onboarding / Off-boarding** – consistent Day-1 experience and no orphan accounts.  
3. **PR Reviewer Round-Robin** – fair code-review load-balancing (< 24 h SLA).  
4. **Simple Data Pre-Processing** – one-shot SQL ⇢ clean CSV URL, no Excel drudgery.  
5. **Task-Log Reminders & Manager Reports** – automated daily nudges + PDF/CSV roll-up.  
6. **CI / CD Auto-Deploy on Merge-to-Main** – image build, cluster upgrade, health-check & rollback.  
7. **Chat Noise Filter & Smart Digest** – 30-second channel summary for 100+ messages.  
8. **Ticket Auto-Assignment (Urgent Complaints)** – sub-5-minute first response, no manual triage.  
9. **End-of-Day Office Log Summariser** – sensors ⇢ LLM summary ⇢ PDF + Slack post.  
10. **Database Refresh / Delete with Approval** – snapshot, wipe, restore seed, audit trail.  
11. **GitHub → Slack Release Notes** – tag-triggered changelog grouped by feature/bug.  
12. **Data Refresh & Dependency Drift Alert** – hourly data pulls and Monday CVE checks.

---

## How It Works

1. **NL Parser** (LangChain + Pydantic) → converts chat text to JSON task-specs  
2. **Prefect-style DAG Engine** → builds & schedules flows dynamically  
3. **Connector Layer** (Slack, Jira, GitHub, Google, DB) → executes atomic steps  
4. **Observability** – Prometheus / Grafana, OpenTelemetry, Jaeger traces  
5. **Secrets & Config** – Vault + `.env` (never committed thanks to `.gitignore`)  

*Full architecture diagram:* <https://lucid.app/lucidspark/3b128df3-6f6b-480b-8581-4f03a60eb3e4>

---

## Tech Stack

Python · FastAPI · Prefect · LangChain    
SQLite / PostgreSQL · Docker · Kubernetes · GitHub Actions · ArgoCD    
RabbitMQ · Redis · FAISS · Hugging Face Models    
React (Flow) + Tailwind · Prometheus · Grafana · ELK/Loki  

---

## Quick Start

```bash
# clone the repo
git clone https://github.com/harshadayini/Bella-Office-Orchestrator.git
cd Bella-Office-Orchestrator

# create env, install deps
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# copy secrets template & fill values
cp .env.example .env          # NEVER commit real creds!

# launch the Streamlit UI
streamlit run app.py
