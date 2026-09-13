# Adaptive Learning & Career Intelligence Agent

[![tests](https://github.com/bezawadamahidhar20-droid/Adaptive-Learning-Career-Intelligence-Agent./actions/workflows/tests.yml/badge.svg)](https://github.com/bezawadamahidhar20-droid/Adaptive-Learning-Career-Intelligence-Agent./actions/workflows/tests.yml)
[![Python 3.12 | 3.13 | 3.14](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)

An interpretable, adaptive assessment and career readiness intelligence platform designed for college students and tech placements.

The intelligence core operates **without Large Language Models (LLMs)**. Every decision — from question selection to career gap ranking — is computed using closed-form psychometric and reinforcement learning algorithms: **Bayesian Knowledge Tracing (BKT)**, **2-Parameter Logistic Item Response Theory (2PL IRT)**, **Maximum Fisher Information Item Selection**, **Multi-Armed Bandits**, and **Forgetting Curve Scheduling**.

---

## 🌟 Key Features

1. **Latent Knowledge Tracing (BKT)**: Tracks latent concept mastery probability $P(L_t)$ per student and updates in real-time following every correct or incorrect response using calibrated transit, guess, and slip parameters.
2. **Psychometric Ability Estimation (2PL IRT)**: Maintains a continuous latent ability estimate ($\theta$) and evaluates item difficulty ($b$) and discrimination ($a$).
3. **Multi-Objective Adaptive Question Selection**: Maximizes test information gain by optimizing:
   $$\text{Score}(q) = w_1 \cdot I(\theta, q) + w_2 \cdot \text{WeaknessBoost}(q) + w_3 \cdot \text{Novelty}(q) - w_4 \cdot \text{RecencyPenalty}(q)$$
4. **Transparent Selection Reasoning**: Exposes transparent, human-readable rationales for every selected question (e.g. *"Selected because Pandas DataFrame mastery is 30% and this item provides high Fisher Information ($I=0.74$) at ability $\theta=0.00$"*).
5. **Career Intelligence & Readiness Scoring**: Maps student mastery against 5 industry tracks (**Data Scientist**, **Data Analyst**, **Backend Developer**, **Frontend Developer**, **AI/ML Engineer**) with weighted benchmark rubrics.
6. **Dynamic Adaptive Roadmaps**: Automatically recalibrates personalized multi-stage learning roadmaps (Foundations $\to$ Applied $\to$ Portfolio Projects $\to$ Placement Prep) as the student demonstrates skill mastery.
7. **Placement Preparation Hub**: Curated technical DSA challenges, quantitative aptitude practice, interview question banks, and resume readiness checklists.
8. **Secure JWT & Database Persistence**: PBKDF2-HMAC-SHA256 password security, JWT bearer tokens, and SQLite persistence with full relational indexing and PostgreSQL migration readiness.

---

## 🏗️ Architecture

```
Adaptive Learning & Career Intelligence Platform
│
├── Intelligence Core (agent/)
│   ├── knowledge/
│   │   ├── bkt.py               # Bayesian Knowledge Tracing (P(L), Transit, Guess, Slip)
│   │   ├── irt.py               # 2PL IRT & Fisher Information (I(theta) = a^2 * P * (1-P))
│   │   └── forgetting.py        # Exponential memory decay & SM-2 spaced repetition
│   ├── assessment/
│   │   ├── question_selector.py # Multi-objective CAT Fisher information selector
│   │   └── assignment_builder.py# Balanced assessment generation (weak/medium/strong)
│   ├── bandit/
│   │   ├── epsilon_greedy.py    # Epsilon-greedy exploration vs exploitation
│   │   └── contextual_bandit.py # LinUCB contextual bandit
│   ├── career/
│   │   ├── role_matcher.py      # 5 Career role profiles & weighted readiness
│   │   └── skill_gap.py         # Explainable gap ranking & recommendations
│   └── agents/                  # Multi-Agent Coordination Subsystem
│       ├── profile_analyzer.py  # Profile ingestion & background analysis
│       ├── skill_analyzer.py    # Skill normalization & descriptive level mapping
│       ├── career_agent.py      # Career suitability & comparative ranking
│       ├── skill_gap_agent.py   # Priority skill gap identification
│       ├── roadmap_agent.py     # Dynamic multi-stage roadmap generator
│       ├── placement_agent.py   # Role-specific placement prep hub
│       └── adaptation_agent.py  # Reactive roadmap adaptation upon assessment
│
├── Backend API Services (backend/)
│   ├── main.py                  # FastAPI application & static mount
│   ├── security.py              # PBKDF2-HMAC-SHA256 hashing & JWT tokens
│   ├── database.py              # SQLite storage with automatic schema migrations
│   ├── schemas.py               # Pydantic request/response data contracts
│   └── routers/                 # auth, onboarding, skills, career, roadmap, placement, assessment, dashboard
│
├── Offline Analytics & Simulation (agent/analytics/)
│   ├── train_calibration.py     # Maximum likelihood parameter calibration on student splits
│   └── offline_simulation.py    # Standalone benchmark comparing Random vs Fixed vs Adaptive
│
└── Frontend Single-Page App (frontend/)
    ├── index.html               # Responsive multi-view dashboard & assessment UI
    ├── index.css                # Custom glassmorphic dark theme design system
    └── app.js                   # Reactive state management & API controllers
```

---

## 📊 Offline Evaluation & Simulation Benchmarks

BKT parameters are fit offline on interaction logs using student-level train/held-out splits.

### Comparative Policy Simulation (100 Students, 20 Questions / Student)

```bash
python -m agent.analytics.offline_simulation
```

| Metric | Random Selection | Fixed-Difficulty (Medium) | Adaptive (BKT + IRT) |
|---|---|---|---|
| **Mean Fisher Information (Efficiency)** | 0.4089 | 0.4706 | **0.5283** |
| **Weak-Concept Targeting Priority** | Baseline | Moderate | **High (60% weak focus)** |
| **Item Discrimination Matching** | Random | Arbitrary | **Optimized at student $\theta$** |
| **Selection Explainability** | None | None | **Full Diagnostic Rationale** |

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Python 3.12, 3.13, or 3.14
- pip / virtualenv

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/bezawadamahidhar20-droid/Adaptive-Learning-Career-Intelligence-Agent.git
cd Adaptive-Learning-Career-Intelligence-Agent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Start the Application
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open your browser to:
- **Web Application:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive OpenAPI Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 🧪 Running the Test Suite

Run all unit, integration, and E2E lifecycle tests:

```bash
python -m pytest -v
```

### Test Coverage Highlights:
- **`agent/tests/`**: 34 psychometric tests covering BKT closed-form equations, 2PL IRT response curves, Fisher Information peaks, LinUCB bandits, and held-out calibration invariant checks.
- **`tests/`**: 13 integration tests covering JWT security, student onboarding normalization, multi-agent coordination, career track benchmarking, placement hub progress, and the complete end-to-end student journey.

---

## 🛠️ Configuration & Environment Variables

Create a `.env` file in the root directory (see `.env.example`):

```env
# Application Environment
APP_ENV=development
PORT=8000

# Security & Authentication
AUTH_SECRET=changeme_replace_with_random_secret
JWT_EXPIRATION_HOURS=72

# Database Connection (SQLite by default; PostgreSQL supported for production)
DATABASE_URL=sqlite:///backend/adaptive_agent.db
```

---

## 🚢 Production Deployment

The platform is designed to deploy seamlessly to containerized and cloud platforms (Render, Railway, Fly.io, AWS, GCP, Heroku):

```bash
# Production start command
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 📄 Documentation

- [Upgrade Audit (UPGRADE_AUDIT.md)](UPGRADE_AUDIT.md)
- [PRD Compliance Report (PRD_COMPLIANCE_REPORT.md)](PRD_COMPLIANCE_REPORT.md)
- [5-Minute Demonstration Script (DEMO_SCRIPT.md)](DEMO_SCRIPT.md)

---

## 📜 License

Distributed under the [MIT License](LICENSE).
