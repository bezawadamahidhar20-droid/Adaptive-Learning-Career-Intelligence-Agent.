# Product Specification: SynapseCAT Adaptive Assessment Platform

**Document Version:** 2026.09 (Release 1 Contract)  
**Status:** Frozen Product Specification  
**Scope:** Phase 1 — Trustworthy Adaptive Assessment Core

---

## 1. Product Mission & Boundaries

SynapseCAT is an explainable psychometric assessment and learning intelligence platform. It measures student concept mastery and psychometric ability using validated statistical cognitive models (Bayesian Knowledge Tracing and 2-Parameter Logistic Item Response Theory with MAP estimation).

### Advisory Disclaimer
> **IMPORTANT ADVISORY NOTICE:**  
> All scores, latent ability estimates ($\theta$), mastery probabilities, and readiness ratings provided by SynapseCAT are **formative, advisory educational measurements** designed solely for learning guidance and self-assessment. They do **not** constitute formal hiring decisions, professional certifications, or employment guarantees.

---

## 2. Separation of the Three Kinds of Truth

SynapseCAT maintains strict separation between three distinct evidence dimensions. These evidence types are stored in separate schemas and are **never collapsed into an unexplained aggregate score**:

| Evidence Type | Primary Data Sources | Representation | Product Interpretation |
| :--- | :--- | :--- | :--- |
| **1. Self-Reported** | Onboarding ratings, profile self-assessment | Prior parameters ($P(L_0)$) | Learner starting belief / prior; **never proof of competence**. |
| **2. Psychometric** | Adaptive CAT items, response accuracy, response times | $\hat{\theta}$, $\text{SE}(\hat{\theta})$, $P(L_t)$, 95% Credible Interval | Latent cognitive ability under test conditions; classified as *Provisional* or *Reliable*. |
| **3. Practical / Demonstrated** | Code execution, test suites passed, project rubrics | Rubric grades, test coverage, artifact depth | Direct proof of hands-on execution; stored with verifiable artifact references. |

---

## 3. Supported Roles & Competency Domains

1. **Data Scientist** (`data_scientist`): Machine Learning, Python, Applied Statistics, SQL, Deep Learning.
2. **Data Analyst** (`data_analyst`): SQL Analytics, Python, Business Statistics, Data Visualization, Data Cleaning.
3. **Backend Developer** (`backend_developer`): REST APIs & System Design, Databases & SQL, Data Structures & Algorithms, Concurrency, Python/Go.
4. **Frontend Developer** (`frontend_developer`): Modern JS/TS, CSS Architecture & Layouts, Web Performance, State Management, Browser APIs.
5. **AI/ML Engineer** (`ai_ml_engineer`): Deep Learning, Transformers & NLP, MLOps & Pipelines, Distributed Systems, PyTorch.

---

## 4. Assessment Types & Stopping Policies

Assessment sessions are parameterized by assessment type with formal multi-criterion stopping policies:

| Policy Parameter | `diagnostic` | `benchmark` | `mastery` | `reassessment` |
| :--- | :---: | :---: | :---: | :---: |
| **Target Purpose** | Rapid initial baseline | Formal progress audit | In-depth skill validation | Delayed retention check |
| **Minimum Items ($N_{\min}$)** | 8 | 15 | 8 | 6 |
| **Maximum Items ($N_{\max}$)** | 15 | 30 | 20 | 15 |
| **Target Posterior SE ($SE_{\text{target}}$)** | 0.40 | 0.30 | 0.35 | 0.35 |
| **Minimum Concept Coverage ($c_{\min}$)** | 60% | 80% | 80% | 60% |
| **Required Critical Concept Checks** | Yes | Yes | Yes | Targeted Only |

### Formal Multi-Criterion Stopping Condition:
$$\text{Stop} = (N \ge N_{\min}) \land \left[ (\text{SE}_{\text{posterior}} \le \text{SE}_{\text{target}}) \lor (N = N_{\max}) \right] \land (\text{Coverage} \ge c_{\min}) \land (\text{Critical Gaps Tested})$$

- **Reliability Determination at Stop:**
  - If $\text{SE}_{\text{posterior}} \le \text{SE}_{\text{target}}$ and $\text{Coverage} \ge c_{\min} \implies \text{"reliable"}$
  - If stopped due to $N = N_{\max}$ with $\text{SE}_{\text{posterior}} > \text{SE}_{\text{target}} \implies \text{"provisional"}$

---

## 5. Psychometric Formulations & Data Contract

### A. Residual Forgetting Floor Model
$$P(L_{\text{decayed}}) = P_{\min} + \left(P(L_{\text{base}}) - P_{\min}\right) \cdot \exp\left(-\lambda_k \cdot \Delta t\right)$$
- $P_{\min} = 0.15$ (Residual knowledge floor).
- $\lambda_k = \lambda_0 \cdot \frac{\text{Difficulty}_k}{\text{PracticeCount}_k + 1} \cdot (2.0 - \text{Accuracy}_k)$ (Skill-specific decay rate).
- Clamped strictly to $[10^{-4}, 1 - 10^{-4}]$.

### B. 2PL IRT & Maximum A Posteriori (MAP) Ability Estimation
$$P(y=1 \mid \theta, a, b) = \frac{1}{1 + \exp\left(-a(\theta - b)\right)}$$
$$\hat{\theta} = \arg\max_{\theta \in [-4, 4]} \left[ \sum_{i=1}^N \left( y_i \ln P_i(\theta) + (1 - y_i) \ln(1 - P_i(\theta)) \right) - \frac{\theta^2}{2 \sigma_{\text{prior}}^2} \right]$$
- Standard normal prior: $\sigma_{\text{prior}} = 1.0$.
- Optimization: Iterative bounded Brent / Newton-Raphson optimizer with tolerance $\epsilon = 10^{-4}$ and max 50 iterations.

### C. Standard Error & Credible Interval Contract
$$\text{Observed Information} = \sum_{i=1}^N I_i(\hat{\theta}) = \sum_{i=1}^N a_i^2 P_i(\hat{\theta})(1 - P_i(\hat{\theta}))$$
$$\text{Prior Information} = \frac{1}{\sigma_{\text{prior}}^2} = 1.0$$
$$\text{SE}_{\text{posterior}}(\hat{\theta}) = \frac{1}{\sqrt{\sum_{i=1}^N I_i(\hat{\theta}) + 1.0}}, \quad \text{SE}_{\text{response\_only}}(\hat{\theta}) = \frac{1}{\sqrt{\sum_{i=1}^N I_i(\hat{\theta})}}$$
$$\text{Raw Interval} = [\hat{\theta} - 1.96 \cdot \text{SE}_{\text{posterior}}, \, \hat{\theta} + 1.96 \cdot \text{SE}_{\text{posterior}}]$$
$$\text{Display Interval} = [\max(-4.0, \text{Raw}_{\text{lower}}), \, \min(4.0, \text{Raw}_{\text{upper}})]$$

---

## 6. Assessment Reliability Data Object

Every completed assessment produces an `AssessmentReliability` record:

```json
{
  "theta": 0.42,
  "posterior_standard_error": 0.27,
  "response_only_standard_error": 0.30,
  "observed_information": 10.84,
  "prior_information": 1.0,
  "raw_interval": [-0.109, 0.949],
  "display_interval": [-0.11, 0.95],
  "scale_bounds": [-4.0, 4.0],
  "near_boundary_warning": false,
  "item_count": 11,
  "concept_count": 6,
  "concept_coverage_ratio": 0.857,
  "reliability_status": "reliable",
  "termination_reason": "target_precision_reached",
  "estimation_method": "MAP",
  "item_bank_version": "2026.09"
}
```

---

## 7. Item Bank Versioning & Quality Control

Item lifecycle: `draft` $\to$ `reviewed` $\to$ `pilot` $\to$ `calibrated` $\to$ `active` $\to$ `retired`.
Every question item records:
- `item_id`: Stable identifier (e.g. `sql-index-001`)
- `concept_id`: Canonical concept reference
- `difficulty` ($b \in [-3, 3]$), `discrimination` ($a \in [0.2, 3]$), `guessing` ($c \approx 0.25$)
- `cognitive_level`: Bloom's taxonomy level (`recall`, `understand`, `apply`, `analyze`, `evaluate`)
- `prerequisites`: Array of prerequisite concept IDs
- `exposure_limit`: Maximum selection frequency (e.g. 0.25)
- `version`: Monotonically increasing version integer
- `status`: `active`
