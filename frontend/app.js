/**
 * SynapseCAT Frontend Application State & Controllers
 */

const API_BASE = "/api";

// App State
const state = {
  currentUser: {
    id: "demo-user-1",
    name: "Alex Rivera",
    email: "alex@university.edu",
    target_role: "data_scientist"
  },
  dashboardData: null,
  rolesList: [],
  currentAssessment: {
    questions: [],
    currentIndex: 0,
    answers: [], // Array of { question_id, selected_option }
    results: null
  }
};

// ==================== INITIALIZATION ====================
document.addEventListener("DOMContentLoaded", async () => {
  await initUser();
  await loadRoles();
  await refreshDashboard();
});

async function initUser() {
  try {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.currentUser)
    });
    if (res.ok) {
      const user = await res.json();
      state.currentUser = user;
      updateUserWidget();
    }
  } catch (err) {
    console.error("Auth init error, using fallback state:", err);
  }
}

function updateUserWidget() {
  const nameEl = document.getElementById("user-display-name");
  const avatarEl = document.getElementById("user-avatar-initial");
  const roleEl = document.getElementById("user-target-role-label");
  
  if (nameEl) nameEl.textContent = state.currentUser.name;
  if (avatarEl) avatarEl.textContent = state.currentUser.name.charAt(0);
  if (roleEl) {
    roleEl.textContent = formatRoleTitle(state.currentUser.target_role);
  }
}

function formatRoleTitle(roleId) {
  const map = {
    "data_scientist": "Data Scientist",
    "backend_developer": "Backend Developer",
    "data_analyst": "Data Analyst"
  };
  return map[roleId] || roleId;
}

// ==================== VIEW NAVIGATION ====================
function switchView(viewName) {
  const views = ["dashboard", "assessment", "results", "career", "theory"];
  views.forEach(v => {
    const viewEl = document.getElementById(`view-${v}`);
    const navBtn = document.getElementById(`btn-tab-${v}`);
    if (viewEl) {
      if (v === viewName) {
        viewEl.classList.add("active");
      } else {
        viewEl.classList.remove("active");
      }
    }
    if (navBtn) {
      if (v === viewName) {
        navBtn.classList.add("active");
      } else {
        navBtn.classList.remove("active");
      }
    }
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (viewName === "dashboard") {
    refreshDashboard();
  } else if (viewName === "career") {
    loadCareerIntelligenceView();
  }
}

// ==================== DASHBOARD CONTROLLER ====================
async function refreshDashboard() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/${state.currentUser.id}`);
    if (!res.ok) return;
    const data = await res.json();
    state.dashboardData = data;
    renderDashboard(data);
  } catch (err) {
    console.error("Failed to load dashboard data:", err);
  }
}

function renderDashboard(data) {
  // 1. Top Metrics
  const readinessValEl = document.getElementById("stat-readiness-val");
  const readinessTargetEl = document.getElementById("stat-readiness-target");
  const jobReadyBadge = document.getElementById("job-ready-badge");
  const circleProgress = document.getElementById("readiness-circle-progress");

  if (readinessValEl) readinessValEl.textContent = `${data.career_readiness}%`;
  if (readinessTargetEl) readinessTargetEl.textContent = `Target: ${data.role_title}`;
  
  if (jobReadyBadge) {
    if (data.is_job_ready) {
      jobReadyBadge.className = "status-chip live-chip";
      jobReadyBadge.textContent = "Job Ready";
    } else {
      jobReadyBadge.className = "status-chip ready-chip";
      jobReadyBadge.textContent = "In Training";
    }
  }

  // Progress ring offset (circumference = 2 * PI * 30 ≈ 188.5)
  if (circleProgress) {
    const total = 188.5;
    const offset = total - (total * (data.career_readiness / 100));
    circleProgress.style.strokeDashoffset = Math.max(0, offset);
  }

  // 2. IRT Theta & Gauge
  const thetaEl = document.getElementById("stat-theta-val");
  const thetaMarker = document.getElementById("theta-gauge-marker");
  if (thetaEl) {
    const sign = data.theta >= 0 ? "+" : "";
    thetaEl.textContent = `${sign}${data.theta.toFixed(2)}`;
  }
  if (thetaMarker) {
    // Map theta [-3.0, +3.0] to [0%, 100%]
    const pct = Math.max(5, Math.min(95, ((data.theta + 3.0) / 6.0) * 100));
    thetaMarker.style.left = `${pct}%`;
  }

  // 3. Priority Gap
  const prioSkillEl = document.getElementById("top-priority-skill-name");
  const prioDescEl = document.getElementById("top-priority-desc");
  if (prioSkillEl) {
    prioSkillEl.textContent = data.top_priority_skill || "All Core Benchmarks Met";
  }
  if (prioDescEl && data.gaps && data.gaps.length > 0) {
    const topGap = data.gaps[0];
    prioDescEl.textContent = `${topGap.recommendation_text}`;
  }

  // 4. Attempts & Accuracy
  const attemptsEl = document.getElementById("stat-attempts-val");
  const accEl = document.getElementById("stat-accuracy-val");
  if (attemptsEl) attemptsEl.innerHTML = `${data.total_attempts} <span class="sub-unit">items</span>`;
  if (accEl) accEl.textContent = `Accuracy: ${data.accuracy_percentage}% | Closed-form Bayesian updates`;

  // 5. Skill Bars
  renderSkillBars(data.skill_masteries);

  // 6. Career Gap Matrix Table
  renderGapTable(data.gaps);

  // 7. Next Assessment Preview
  const launchDesc = document.getElementById("next-assessment-desc");
  const conceptsTags = document.getElementById("target-concepts-preview");
  if (launchDesc && data.top_priority_skill) {
    launchDesc.innerHTML = `Fisher-information CAT prioritized targeted questions focusing on <strong>${data.top_priority_skill}</strong> to optimize learning gain.`;
  }
  if (conceptsTags && data.next_recommended_assignment) {
    conceptsTags.innerHTML = data.next_recommended_assignment.map(q => `
      <span class="concept-tag"><i class="fa-solid fa-bolt"></i> ${q.concept}</span>
    `).join("");
  }
}

function renderSkillBars(skills) {
  const container = document.getElementById("skill-bars-list");
  if (!container) return;

  const defaultSkills = {
    "Python": 0.50,
    "Machine Learning": 0.35,
    "SQL": 0.45,
    "Statistics": 0.40,
    "Deep Learning": 0.20
  };

  const activeSkills = (skills && Object.keys(skills).length > 0) ? skills : defaultSkills;
  const gradientClasses = ["fill-gradient-cyan", "fill-gradient-indigo", "fill-gradient-emerald", "fill-gradient-amber"];

  container.innerHTML = Object.entries(activeSkills).map(([name, val], idx) => {
    const pct = Math.round(val * 100);
    const grad = gradientClasses[idx % gradientClasses.length];
    return `
      <div class="skill-bar-row">
        <div class="skill-bar-meta">
          <span class="skill-bar-name">${name}</span>
          <span class="skill-bar-pct">${pct}%</span>
        </div>
        <div class="skill-track">
          <div class="skill-fill ${grad}" style="width: ${pct}%;"></div>
        </div>
      </div>
    `;
  }).join("");
}

function renderGapTable(gaps) {
  const tbody = document.getElementById("gap-table-body");
  if (!tbody) return;

  if (!gaps || gaps.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No active gaps recorded.</td></tr>`;
    return;
  }

  tbody.innerHTML = gaps.map(g => `
    <tr>
      <td><strong>#${g.priority_rank}</strong></td>
      <td><strong>${g.skill}</strong></td>
      <td>${Math.round(g.current_mastery * 100)}%</td>
      <td>${Math.round(g.target_threshold * 100)}%</td>
      <td><span class="badge ${g.gap_magnitude > 0.05 ? 'badge-purple' : 'badge-cyan'}">${g.gap_magnitude.toFixed(3)}</span></td>
    </tr>
  `).join("");
}

// ==================== ADAPTIVE ASSESSMENT CONTROLLER ====================
async function startNewAssessment(questionCount = 10) {
  switchView("assessment");

  try {
    const res = await fetch(`${API_BASE}/assessment/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser.id,
        total_questions: questionCount,
        target_role: state.currentUser.target_role
      })
    });

    if (!res.ok) throw new Error("Failed to generate test");
    const questions = await res.json();

    state.currentAssessment = {
      questions: questions,
      currentIndex: 0,
      answers: [],
      results: null
    };

    renderQuestion();
  } catch (err) {
    console.error("Error launching assessment:", err);
  }
}

function renderQuestion() {
  const { questions, currentIndex } = state.currentAssessment;
  if (!questions || questions.length === 0) return;

  const q = questions[currentIndex];

  // Header badges
  document.getElementById("test-skill-badge").textContent = q.skill;
  document.getElementById("test-concept-badge").textContent = q.concept;
  document.getElementById("test-diff-badge").textContent = `Diff ${q.difficulty}/5`;
  document.getElementById("current-q-index").textContent = currentIndex + 1;
  document.getElementById("total-q-count").textContent = questions.length;

  // Progress Bar
  const progressPct = ((currentIndex + 1) / questions.length) * 100;
  document.getElementById("assessment-progress-fill").style.width = `${progressPct}%`;

  // Question content
  document.getElementById("q-subtopic-text").textContent = `Subtopic: ${q.subtopic || q.concept}`;
  document.getElementById("question-text").textContent = q.question;

  // Options
  const container = document.getElementById("options-container");
  container.innerHTML = q.options.map((opt, idx) => `
    <button class="option-btn" id="opt-btn-${idx}" onclick="selectOption(${idx})">
      <div class="opt-index">${String.fromCharCode(65 + idx)}</div>
      <div class="opt-text">${opt}</div>
    </button>
  `).join("");

  // Reset feedback and Next button
  document.getElementById("answer-feedback-box").classList.add("hidden");
  document.getElementById("btn-next-question").classList.add("hidden");
}

async function selectOption(chosenIdx) {
  const { questions, currentIndex } = state.currentAssessment;
  const q = questions[currentIndex];

  // Disable all options
  const optionButtons = document.querySelectorAll(".option-btn");
  optionButtons.forEach(btn => btn.disabled = true);

  // Store answer
  state.currentAssessment.answers.push({
    question_id: q.id,
    selected_option: chosenIdx
  });

  // Submit single answer to get immediate BKT/IRT feedback
  try {
    const submitRes = await fetch(`${API_BASE}/assessment/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.currentUser.id,
        target_role: state.currentUser.target_role,
        submissions: [{ question_id: q.id, selected_option: chosenIdx }]
      })
    });

    if (submitRes.ok) {
      const respData = await submitRes.json();
      const answerRes = respData.results[0];

      // Highlight selected option
      const chosenBtn = document.getElementById(`opt-btn-${chosenIdx}`);
      const correctBtn = document.getElementById(`opt-btn-${answerRes.correct_option}`);

      if (answerRes.is_correct) {
        if (chosenBtn) chosenBtn.classList.add("selected-correct");
      } else {
        if (chosenBtn) chosenBtn.classList.add("selected-wrong");
        if (correctBtn) correctBtn.classList.add("selected-correct");
      }

      // Show Feedback Box
      const feedbackBox = document.getElementById("answer-feedback-box");
      const titleEl = document.getElementById("feedback-status-title");
      const expEl = document.getElementById("feedback-explanation-text");
      const deltaEl = document.getElementById("feedback-mastery-delta");

      feedbackBox.classList.remove("hidden");
      if (answerRes.is_correct) {
        titleEl.className = "feedback-header correct";
        titleEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> Correct Response`;
      } else {
        titleEl.className = "feedback-header incorrect";
        titleEl.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> Incorrect Response`;
      }

      expEl.textContent = answerRes.explanation;
      const prevM = (answerRes.previous_mastery * 100).toFixed(1);
      const nextM = (answerRes.updated_mastery * 100).toFixed(1);
      const diffSign = answerRes.updated_mastery >= answerRes.previous_mastery ? "+" : "";
      const diffM = (answerRes.updated_mastery - answerRes.previous_mastery) * 100;
      deltaEl.innerHTML = `<span>BKT Mastery for <strong>${answerRes.concept}</strong>: ${prevM}% → <strong>${nextM}%</strong> (${diffSign}${diffM.toFixed(1)}%)</span>`;

      // Show Next button
      const nextBtn = document.getElementById("btn-next-question");
      nextBtn.classList.remove("hidden");
      if (currentIndex === questions.length - 1) {
        nextBtn.innerHTML = `<span>View Final Results</span> <i class="fa-solid fa-award"></i>`;
      } else {
        nextBtn.innerHTML = `<span>Next Question</span> <i class="fa-solid fa-arrow-right"></i>`;
      }
    }
  } catch (err) {
    console.error("Error submitting answer:", err);
  }
}

function nextQuestion() {
  const { questions, currentIndex } = state.currentAssessment;
  if (currentIndex < questions.length - 1) {
    state.currentAssessment.currentIndex += 1;
    renderQuestion();
  } else {
    // Show results
    showResultsView();
  }
}

async function showResultsView() {
  switchView("results");
  await refreshDashboard();

  const data = state.dashboardData;
  if (data) {
    document.getElementById("result-score-val").textContent = `${data.accuracy_percentage}%`;
    document.getElementById("result-correct-ratio").textContent = `${data.correct_attempts} / ${data.total_attempts} Total`;
    document.getElementById("result-theta-val").textContent = `${data.theta >= 0 ? '+' : ''}${data.theta.toFixed(2)}`;
    document.getElementById("result-readiness-val").textContent = `${data.career_readiness}%`;

    // Render Mastery list
    const container = document.getElementById("results-mastery-list");
    if (container && data.concept_masteries) {
      container.innerHTML = Object.entries(data.concept_masteries).map(([c, m]) => `
        <div class="breakdown-item">
          <span class="b-concept">${c}</span>
          <span class="b-delta text-cyan">${Math.round(m * 100)}% Mastery</span>
        </div>
      `).join("");
    }
  }
}

// ==================== CAREER INTELLIGENCE VIEW ====================
async function loadRoles() {
  try {
    const res = await fetch(`${API_BASE}/career/roles`);
    if (res.ok) {
      state.rolesList = await res.json();
    }
  } catch (err) {
    console.error("Failed to load roles:", err);
  }
}

async function loadCareerIntelligenceView() {
  const roleId = state.currentUser.target_role;
  const selectEl = document.getElementById("career-role-select");
  if (selectEl) selectEl.value = roleId;

  try {
    const res = await fetch(`${API_BASE}/career/analyze/${state.currentUser.id}/${roleId}`);
    if (!res.ok) return;
    const report = await res.json();

    document.getElementById("career-detail-role-title").textContent = report.role_title;

    // Find role info
    const roleInfo = state.rolesList.find(r => r.role_id === roleId);
    if (roleInfo) {
      document.getElementById("career-detail-role-desc").textContent = roleInfo.description;
      const weightsContainer = document.getElementById("role-weights-container");
      if (weightsContainer) {
        weightsContainer.innerHTML = Object.entries(roleInfo.skill_weights).map(([skill, weight]) => `
          <div class="weight-row">
            <span><strong>${skill}</strong></span>
            <span class="badge badge-purple">${Math.round(weight * 100)}% Weight</span>
          </div>
        `).join("");
      }
    }

    // Action plan items
    const actionList = document.getElementById("career-action-items-list");
    if (actionList) {
      actionList.innerHTML = report.gaps.map(g => `
        <div class="action-card-item">
          <div class="action-card-header">
            <span class="action-skill-title">${g.skill}</span>
            <span class="badge ${g.gap_magnitude > 0.05 ? 'badge-diff' : 'badge-cyan'}">Priority #${g.priority_rank}</span>
          </div>
          <p class="action-desc">${g.recommendation_text}</p>
          <div class="card-action-link">Target: ${Math.round(g.target_threshold * 100)}% | Current: ${Math.round(g.current_mastery * 100)}%</div>
        </div>
      `).join("");
    }

  } catch (err) {
    console.error("Failed to load career analysis:", err);
  }
}

async function changeTargetRole(newRole) {
  state.currentUser.target_role = newRole;
  updateUserWidget();
  await loadCareerIntelligenceView();
  await refreshDashboard();
}

// ==================== MODAL CONTROLS ====================
function openProfileModal() {
  const modal = document.getElementById("profile-modal");
  document.getElementById("modal-input-name").value = state.currentUser.name;
  document.getElementById("modal-select-role").value = state.currentUser.target_role;
  modal.classList.remove("hidden");
}

function closeProfileModal() {
  document.getElementById("profile-modal").classList.add("hidden");
}

async function saveProfileModal() {
  const newName = document.getElementById("modal-input-name").value;
  const newRole = document.getElementById("modal-select-role").value;

  state.currentUser.name = newName;
  state.currentUser.target_role = newRole;
  closeProfileModal();
  updateUserWidget();
  await refreshDashboard();
}
