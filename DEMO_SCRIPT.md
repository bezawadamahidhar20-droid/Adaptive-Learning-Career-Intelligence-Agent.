# 5-Minute Product Demonstration Script

**Project:** Adaptive Learning & Career Intelligence Agent  
**Platform:** FastAPI + Vanilla Glassmorphic Web Client + BKT/IRT/Bandit Multi-Agent Core  
**Duration:** ~5 Minutes

---

## 🎯 Demo Goal
Demonstrate to evaluators and students how the platform uses psychometric algorithms (Bayesian Knowledge Tracing and 2PL Item Response Theory) to deliver a personalized, explainable learning and career readiness journey with zero LLM hallucinations.

---

## ⏱️ Step-by-Step Demo Flow

### Minute 1: Student Registration & Intelligent Onboarding
1. **Launch Platform:**
   - Open `http://127.0.0.1:8000/` in browser.
2. **Registration / Auth:**
   - Click **"Sign In"** or create a new student account (e.g. `scholar@university.edu`).
   - Notice the secure JWT authentication flow and clean glassmorphism dark UI.
3. **Onboarding Wizard:**
   - Complete the onboarding modal: Select **Education Level** (e.g. *Undergraduate B.Tech CS*), **Graduation Year** (*2026*), and **Target Role Track** (e.g. *Data Scientist*).
   - Rate initial baseline familiarity across core technical skills (*Python: Good, SQL: Average, Machine Learning: Below Average*).
   - Click **"Complete Onboarding"**.

---

### Minute 2: Real-Time Career Intelligence & Dashboard Inspection
1. **Dashboard Overview:**
   - Observe the **Live Career Readiness Score** (e.g. ~48.5%) calculated by weighting current skill masteries against industry benchmark rubrics.
   - Inspect the **Explainable Career Justification Banner**:
     > *"Recommended to improve Machine Learning and Statistics: currently below the 80% benchmark for Data Scientist."*
2. **Prioritized Skill Matrix:**
   - View the skill cards categorized by proficiency levels (*Good*, *Average*, *Below Average*) and priority rankings.
3. **Dynamic Roadmap Preview:**
   - View the personalized milestones generated dynamically based on identified skill gaps.

---

### Minute 3: Adaptive Assessment & Transparent Selection Insight
1. **Launch Adaptive Assessment:**
   - Click **"Launch Adaptive Test (10 Qs)"**.
2. **Inspect Adaptive Question Selection Insight:**
   - Point out the **Adaptive Selection Insight Banner** at the top of each question:
     > *"💡 Selected because 'Pandas DataFrames' mastery is 30% (low) and this question provides high diagnostic information (I=0.74) at ability θ=0.00."*
   - Highlight that question selection is mathematically driven by **Fisher Information optimization** and **weak-concept prioritization**, not random selection.
3. **Interactive Answer Submission:**
   - Select an answer option.
   - Observe the instantaneous real-time feedback with conceptual explanation and BKT mastery delta.

---

### Minute 4: Assessment Completion & Psychometric State Updates
1. **Complete Assessment:**
   - Answer the remaining questions in the adaptive sequence.
2. **Results Screen Analysis:**
   - View the updated **Psychometric Ability ($\theta$)** (converged CAT ability).
   - View the **Knowledge Tracing Breakdown** showing exact before-and-after posterior mastery transitions for each concept:
     - e.g., *Pandas DataFrames: 30.0% $\to$ 64.2% (+34.2%)*
     - e.g., *Window Functions: 20.0% $\to$ 48.1% (+28.1%)*
3. **Return to Dashboard:**
   - Click **"Return to Dashboard"** and observe that the overall **Career Readiness Score** has dynamically increased to reflect the new mastery data!

---

### Minute 5: Cross-Role Benchmarking & Placement Preparation Hub
1. **Career Track Switching:**
   - Navigate to the **"Career Intelligence"** tab in the top navigation.
   - Switch target career track from *Data Scientist* to *Backend Developer* or *AI/ML Engineer*.
   - Observe instant recalibration of readiness scores, skill requirements, and gap rankings.
2. **Placement Preparation Hub:**
   - Navigate to the **"Placement Hub"** tab.
   - Explore role-specific **DSA Problem Sets**, **Aptitude Practice**, and **Technical Interview Flashcards**.
   - Check off completed challenges and observe progress tracking.
3. **Persistence Verification:**
   - Refresh the web browser (`F5`).
   - Confirm all mastery updates, attempt histories, and roadmap progress persist seamlessly from the SQLite database.
