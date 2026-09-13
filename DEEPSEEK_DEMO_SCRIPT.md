# SynapseCAT — 5-Minute Interactive Live Demo Script

**Project:** Adaptive Learning & Career Intelligence Agent  
**Live URL:** `http://127.0.0.1:8000/`  
**API Health Check:** `http://127.0.0.1:8000/api/health`

---

## Demo Overview

This script guides an evaluator, recruiter, or engineer through the complete end-to-end capabilities of the **SynapseCAT** platform in under 5 minutes. Every feature runs live against real mathematical models (BKT, IRT 2PL, Fisher Information, and LinUCB Bandits) and persistent SQLite storage.

---

## Step-by-Step Walkthrough

### Step 1: Launch Application & Server
1. In your terminal, run the FastAPI backend server:
   ```bash
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Open your browser and navigate to:
   ```
   http://127.0.0.1:8000/
   ```
3. The application will initialize and present the dark glassmorphism dashboard.

---

### Step 2: Student Registration & Authentication
1. Click the **Account / Switch User** button in the top right navbar (`#btn-auth-menu`).
2. Toggle to **Create Account** mode.
3. Enter new credentials:
   - **Full Name:** `Sarah Chen`
   - **Email:** `sarah.chen@university.edu`
   - **Password:** `Placement2026!`
4. Click **Create Account**.
5. *Evidence:* A secure PBKDF2-hashed user is created with a signed JWT Bearer Token stored in `localStorage`.

---

### Step 3: Student Onboarding & Career Goal Selection
1. The **Career & Skills Onboarding Wizard** automatically appears:
   - **Education Background:** `Undergraduate (B.Tech / B.S. CS)`
   - **Target Placement Year:** `2026`
   - **Primary Career Track:** `Data Scientist (ML, Stats, Python, SQL)`
   - **Skill Self-Ratings:**
     - Python: `Good`
     - SQL: `Average`
     - Machine Learning: `Below Average`
     - Statistics: `Below Average`
     - Data Structures & Algorithms: `Average`
2. Click **Complete Onboarding & Launch Dashboard**.
3. *Evidence:* The multi-agent orchestrator maps descriptive ratings into quantitative baseline masteries, saves them to `knowledge_states`, and computes initial career readiness.

---

### Step 4: Inspect Personalized Dashboard
1. Review the Top 5 Metrics:
   - **Overall Mastery:** Shows initial calibrated baseline mastery across role concepts.
   - **Career Readiness:** Shows weighted suitability percentage against the Data Scientist benchmark.
   - **Psychometric Ability ($\theta$):** Calibrating state $[-4.0, +4.0]$.
   - **Top Priority Focus:** Identifies `Machine Learning` or `Statistics` as the highest-leverage gap.
   - **Online BKT Updates:** Shows 0 items initially.
2. Review **Strongest vs Weakest Skills** pills and the **Recommended Next Learning Step** banner.

---

### Step 5: Launch Adaptive CAT Assessment
1. Click **Launch Adaptive Test (10 Qs)** or click the **Adaptive Test** tab in the navbar.
2. Observe Question 1:
   - Inspect the **Selection Reason Pill**: Explains why this specific item was chosen (e.g. *Selected to maximize Fisher information on low mastery concept*).
   - Answer the question.
   - Click your choice: Immediate feedback displays with **Correct/Incorrect status**, detailed explanation, and real-time **BKT Mastery Delta** ($P(L_{t}) \rightarrow P(L_{t+1})$).
3. Proceed through all 10 questions:
   - Notice how subsequent questions adapt difficulty based on whether prior answers were correct or incorrect (IRT 2PL ability convergence).

---

### Step 6: Psychometric Results & Knowledge Tracing Convergence
1. On completing Question 10, click **View Psychometric Results**.
2. Review:
   - Final Assessment Score & Accuracy.
   - Converged Psychometric Ability ($\theta$).
   - Updated Career Suitability percentage.
   - Concept-by-concept BKT knowledge transitions table.
3. Click **Return to Dashboard**.

---

### Step 7: Dynamic Adaptive Roadmap Recalibration
1. Navigate to the **Adaptive Roadmap** tab.
2. Observe how roadmap milestones (Foundations, Core Engineering, Advanced Placement, Capstone) reflect updated mastery states.
3. Check off a completed milestone task.
4. Refresh the page: Observe that task status is persisted across reloads.

---

### Step 8: Placement Preparation Hub
1. Navigate to the **Placement Prep** tab.
2. Explore the 4 specialized role preparation modules:
   - **Technical DSA:** Review problem formulations, difficulty tags, and collapsible solution approaches.
   - **Aptitude Practice:** Interactive aptitude questions with step-by-step mathematical reasoning.
   - **Interview Q&A:** Technical and HR interview questions with model answers formatted using the **STAR** (Situation, Task, Action, Result) framework.
   - **Resume & Profile Checklist:** Tailored criteria for tech placement screenings.

---

### Step 9: Career Intelligence Hub & Role Switching
1. Navigate to the **Career Hub** tab.
2. Review the skill weight breakdown for **Data Scientist**.
3. Inspect the **Multi-Role Suitability Rankings** comparing the student's profile across all 5 career tracks.
4. Change the dropdown to **AI/ML Engineer** or **Backend Developer**:
   - The system automatically re-evaluates weighted fit and recalibrates priority skill gaps.

---

### Step 10: Profile & Agent Core Theory
1. Click the **Profile** tab:
   - Review comprehensive student metadata, BKT mastery distribution meters, and historical assessment records.
2. Click the **Agent Core** tab:
   - Inspect the mathematical formulas for Bayesian Knowledge Tracing, 2PL IRT, Fisher Information, and Multi-Armed Bandit policies powering the system.

---

## Demo Verification Summary

| Feature | Verified Live |
| :--- | :---: |
| Student Registration & JWT Security | Yes |
| Onboarding & Baseline Calibration | Yes |
| Adaptive Question Selection with Reason | Yes |
| Real-Time BKT State Update & Delta | Yes |
| 2PL IRT Ability Estimation ($\theta$) | Yes |
| Career Readiness & 5 Role Tracks | Yes |
| Dynamic Roadmap Milestone Tracking | Yes |
| Technical Placement Preparation Modules | Yes |
| SQLite State Persistence Across Restarts | Yes |
