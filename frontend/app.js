/**
 * SynapseCAT Production Frontend Application State & Controllers
 */

const API_BASE = "/api";

// App State
const state = {
  token: localStorage.getItem("synapsecat_jwt") || null,
  currentUser: null,
  dashboardData: null,
  rolesList: [],
  currentAssessment: {
    questions: [],
    currentIndex: 0,
    answers: [],
    results: null
  },
  currentPlacementTab: "dsa",
  authMode: "login" // 'login' or 'register'
};

// ==================== INITIALIZATION ====================
document.addEventListener("DOMContentLoaded", async () => {
  await bootstrapApp();
});

async function bootstrapApp() {
  if (state.token) {
    const ok = await fetchCurrentUser();
    if (ok) {
      await initializeAuthenticatedSession();
      return;
    }
  }

  // Auto-login default scholar user for seamless review/demo
  await autoLoginDefaultScholar();
}

async function autoLoginDefaultScholar() {
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "alex@university.edu", password: "Password123!" })
    });

    if (res.ok) {
      const data = await res.json();
      state.token = data.access_token;
      state.currentUser = data.user;
      localStorage.setItem("synapsecat_jwt", state.token);
      await initializeAuthenticatedSession();
    } else {
      // Register default scholar if not exists
      const regRes = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Alex Rivera",
          email: "alex@university.edu",
          password: "Password123!",
          target_role: "data_scientist"
        })
      });
      if (regRes.ok) {
        const data = await regRes.json();
        state.token = data.access_token;
        state.currentUser = data.user;
        localStorage.setItem("synapsecat_jwt", state.token);
        await initializeAuthenticatedSession();
      }
    }
  } catch (err) {
    console.error("Auto login error:", err);
  }
}

async function fetchCurrentUser() {
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders()
    });
    if (res.ok) {
      state.currentUser = await res.json();
      updateUserWidget();
      return true;
    } else {
      state.token = null;
      localStorage.removeItem("synapsecat_jwt");
      return false;
    }
  } catch (err) {
    console.error("Fetch current user failed:", err);
    return false;
  }
}

async function initializeAuthenticatedSession() {
  updateUserWidget();
  await loadRoles();

  // Enforce mandatory onboarding if not completed
  if (state.currentUser && !state.currentUser.onboarding_completed) {
    openOnboardingModal();
    return;
  }

  await refreshDashboard();
}

function getAuthHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  return headers;
}

function updateUserWidget() {
  const nameEl = document.getElementById("user-display-name");
  const avatarEl = document.getElementById("user-avatar-initial");
  const roleEl = document.getElementById("user-target-role-label");
  
  if (state.currentUser) {
    if (nameEl) nameEl.textContent = state.currentUser.name;
    if (avatarEl) avatarEl.textContent = state.currentUser.name.charAt(0);
    if (roleEl) roleEl.textContent = formatRoleTitle(state.currentUser.target_role);
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
  const views = ["dashboard", "roadmap", "placement", "assessment", "results", "career", "theory"];
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

  if (viewName === "dashboard") refreshDashboard();
  else if (viewName === "roadmap") loadRoadmapView();
  else if (viewName === "placement") loadPlacementView();
  else if (viewName === "career") loadCareerView();
}

// ==================== DASHBOARD CONTROLLER ====================
async function refreshDashboard() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const data = await res.json();
    state.dashboardData = data;
    renderDashboard(data);
  } catch (err) {
    console.error("Dashboard load error:", err);
  }
}

function renderDashboard(data) {
  // 1. Readiness & Badge
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

  if (circleProgress) {
    const total = 188.5;
    const offset = total - (total * (data.career_readiness / 100));
    circleProgress.style.strokeDashoffset = Math.max(0, offset);
  }

  // 2. IRT Theta
  const thetaEl = document.getElementById("stat-theta-val");
  const thetaSub = document.getElementById("stat-theta-sub");
  const thetaMarker = document.getElementById("theta-gauge-marker");
  if (thetaEl) {
    if (!data.has_sufficient_data) {
      thetaEl.textContent = "Calibrating";
      if (thetaSub) thetaSub.textContent = "Not enough data yet (Take 1st test)";
    } else {
      const sign = data.theta >= 0 ? "+" : "";
      thetaEl.textContent = `${sign}${data.theta.toFixed(2)}`;
      if (thetaSub) thetaSub.textContent = "Range: [-4.0, +4.0] (Std Normal)";
    }
  }
  if (thetaMarker) {
    const pct = Math.max(5, Math.min(95, ((data.theta + 3.0) / 6.0) * 100));
    thetaMarker.style.left = `${pct}%`;
  }

  // 3. Priority Focus
  const prioSkillEl = document.getElementById("top-priority-skill-name");
  const prioDescEl = document.getElementById("top-priority-desc");
  if (prioSkillEl) prioSkillEl.textContent = data.top_priority_skill || "General Calibration";
  if (prioDescEl) {
    if (data.skills && data.skills.length > 0) {
      prioDescEl.textContent = data.skills[0].improvement_recommendation;
    }
  }

  // 4. Attempts & Accuracy
  const attemptsEl = document.getElementById("stat-attempts-val");
  const accEl = document.getElementById("stat-accuracy-val");
  if (attemptsEl) attemptsEl.innerHTML = `${data.total_attempts} <span class="sub-unit">items</span>`;
  if (accEl) {
    accEl.textContent = data.has_sufficient_data 
      ? `Accuracy: ${data.accuracy_percentage}% | Online BKT state active`
      : "Not enough data yet | Take your first test below";
  }

  // 5. Explainable Justification Banner
  const expText = document.getElementById("career-explanation-text");
  if (expText && data.career_fit) {
    expText.textContent = data.career_fit.explanation;
  }

  // 6. Prioritized Skill Cards
  renderSkillCards(data.skills);

  // 7. Roadmap Preview
  renderDashboardRoadmapPreview(data.roadmap_preview);

  // 8. Next Assessment Preview
  const launchDesc = document.getElementById("next-assessment-desc");
  const conceptsTags = document.getElementById("target-concepts-preview");
  if (launchDesc && data.top_priority_skill) {
    launchDesc.innerHTML = `Fisher-information CAT prioritized targeted items focusing on <strong>${data.top_priority_skill}</strong>.`;
  }
  if (conceptsTags && data.next_recommended_assignment) {
    conceptsTags.innerHTML = data.next_recommended_assignment.map(q => `
      <span class="concept-tag"><i class="fa-solid fa-bolt"></i> ${q.concept}</span>
    `).join("");
  }
}

function renderSkillCards(skills) {
  const container = document.getElementById("skill-cards-container");
  if (!container) return;

  if (!skills || skills.length === 0) {
    container.innerHTML = `<div class="p-card-empty">No skills recorded yet. Complete onboarding.</div>`;
    return;
  }

  container.innerHTML = skills.map(s => {
    const badgeClass = s.descriptive_level.toLowerCase().replace(/\s+/g, '-');
    return `
      <div class="skill-item-card">
        <div class="skill-card-top">
          <span class="skill-card-name">${s.skill_name}</span>
          <span class="level-badge ${badgeClass}">${s.descriptive_level}</span>
        </div>
        <p class="skill-card-rec">${s.improvement_recommendation}</p>
        <div class="skill-card-meta">
          <span>Target: ${s.target_level}</span>
          <span>Priority #${s.priority_rank}</span>
        </div>
      </div>
    `;
  }).join("");
}

function renderDashboardRoadmapPreview(tasks) {
  const container = document.getElementById("dashboard-roadmap-preview");
  if (!container) return;

  if (!tasks || tasks.length === 0) {
    container.innerHTML = `<div class="p-card-empty">All initial roadmap milestones completed!</div>`;
    return;
  }

  container.innerHTML = tasks.map(t => `
    <div class="task-item-row">
      <input type="checkbox" class="task-checkbox" onchange="toggleTaskStatus('${t.id}', this.checked)" ${t.is_completed ? 'checked' : ''}>
      <div class="task-body">
        <div class="task-title">${t.title}</div>
        <div class="task-desc">${t.description}</div>
      </div>
    </div>
  `).join("");
}

// ==================== ROADMAP CONTROLLER ====================
async function loadRoadmapView() {
  try {
    const res = await fetch(`${API_BASE}/roadmap/`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const data = await res.json();
    renderRoadmapView(data);
  } catch (err) {
    console.error("Roadmap load error:", err);
  }
}

function renderRoadmapView(data) {
  const counterEl = document.getElementById("roadmap-completion-counter");
  if (counterEl) {
    counterEl.textContent = `${data.completed_tasks} / ${data.total_tasks} Tasks (${data.completion_percentage}%) Completed`;
  }

  const container = document.getElementById("roadmap-stages-container");
  if (!container) return;

  container.innerHTML = Object.entries(data.stages).map(([stageName, tasks]) => `
    <div class="roadmap-stage-block">
      <h3 class="stage-title"><i class="fa-solid fa-flag-checkered"></i> ${stageName}</h3>
      <div class="stage-tasks-list">
        ${tasks.map(t => `
          <div class="task-item-row ${t.is_completed ? 'completed' : ''}">
            <input type="checkbox" class="task-checkbox" onchange="toggleTaskStatus('${t.id}', this.checked)" ${t.is_completed ? 'checked' : ''}>
            <div class="task-body">
              <div class="task-title">${t.title}</div>
              <div class="task-desc">${t.description}</div>
              <div class="task-badges">
                <span class="badge badge-purple">${t.associated_skill}</span>
                <span class="badge badge-cyan">${t.category.replace('_', ' ').toUpperCase()}</span>
              </div>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
}

async function toggleTaskStatus(taskId, isCompleted) {
  try {
    await fetch(`${API_BASE}/roadmap/toggle-task`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ task_id: taskId, is_completed: isCompleted })
    });
    await refreshDashboard();
    if (document.getElementById("view-roadmap").classList.contains("active")) {
      await loadRoadmapView();
    }
  } catch (err) {
    console.error("Toggle task error:", err);
  }
}

// ==================== PLACEMENT PREPARATION CONTROLLER ====================
async function loadPlacementView() {
  try {
    const res = await fetch(`${API_BASE}/placement/modules`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const modules = await res.json();
    renderPlacementModules(modules);
  } catch (err) {
    console.error("Placement load error:", err);
  }
}

function switchPlacementTab(tabKey) {
  state.currentPlacementTab = tabKey;
  document.querySelectorAll(".p-tab").forEach(b => b.classList.remove("active"));
  const btn = document.getElementById(`ptab-${tabKey}`);
  if (btn) btn.classList.add("active");
  loadPlacementView();
}

function renderPlacementModules(modules) {
  const container = document.getElementById("placement-module-content");
  if (!container) return;

  const currentMod = modules.find(m => m.module_type === state.currentPlacementTab) || modules[0];
  if (!currentMod) return;

  let html = `
    <div class="panel-header">
      <div>
        <h3 class="panel-title">${currentMod.title}</h3>
        <p class="panel-desc">${currentMod.description}</p>
      </div>
    </div>
    <div class="challenges-list">
  `;

  if (currentMod.module_type === "dsa") {
    html += currentMod.items.map(item => `
      <div class="challenge-card">
        <div class="flex-center-between">
          <span class="challenge-title">${item.title}</span>
          <span class="badge badge-diff">${item.difficulty}</span>
        </div>
        <p class="challenge-problem">${item.problem}</p>
        <div class="solution-collapsible">
          <strong>Key Concept:</strong> ${item.key_concept}<br>
          <strong>Approach:</strong> ${item.solution_approach}
        </div>
      </div>
    `).join("");
  } else if (currentMod.module_type === "aptitude") {
    html += currentMod.items.map((item, idx) => `
      <div class="challenge-card">
        <span class="challenge-title">${idx + 1}. ${item.title}</span>
        <p class="challenge-problem">${item.question}</p>
        <div class="options-grid" style="margin-top: 0.5rem;">
          ${item.options.map((opt, oIdx) => `
            <div class="option-btn" style="padding: 0.5rem 1rem; pointer-events: none;">
              <span class="opt-index">${String.fromCharCode(65 + oIdx)}</span> ${opt}
            </div>
          `).join("")}
        </div>
        <div class="solution-collapsible">
          <strong>Correct Option:</strong> ${item.options[item.correct_option]}<br>
          <strong>Explanation:</strong> ${item.explanation}
        </div>
      </div>
    `).join("");
  } else if (currentMod.module_type === "interview_qa") {
    html += currentMod.items.map((item, idx) => `
      <div class="challenge-card">
        <div class="flex-center-between">
          <span class="challenge-title">${idx + 1}. ${item.question}</span>
          <span class="badge ${item.type === 'technical' ? 'badge-cyan' : 'badge-purple'}">${item.type.toUpperCase()}</span>
        </div>
        <div class="solution-collapsible" style="color: var(--text-primary); margin-top: 0.5rem;">
          <strong class="text-cyan">Model Response (STAR Framework):</strong><br>
          ${item.model_answer}
        </div>
      </div>
    `).join("");
  } else if (currentMod.module_type === "resume_checklist") {
    html += currentMod.items.map((item, idx) => `
      <div class="task-item-row" style="margin-bottom: 0.75rem;">
        <input type="checkbox" class="task-checkbox" checked disabled>
        <div class="task-body">
          <div class="task-title">${item.title}</div>
          <div class="task-desc">${item.description}</div>
        </div>
      </div>
    `).join("");
  }

  html += `</div>`;
  container.innerHTML = html;
}

// ==================== CAREER VIEW CONTROLLER ====================
async function loadRoles() {
  try {
    const res = await fetch(`${API_BASE}/career/roles`);
    if (res.ok) state.rolesList = await res.json();
  } catch (err) {
    console.error("Load roles error:", err);
  }
}

async function loadCareerView() {
  try {
    const res = await fetch(`${API_BASE}/career/compare`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) return;
    const comparisons = await res.json();

    const targetRole = state.currentUser ? state.currentUser.target_role : "data_scientist";
    const selectEl = document.getElementById("career-role-select");
    if (selectEl) selectEl.value = targetRole;

    const roleInfo = state.rolesList.find(r => r.role_id === targetRole);
    if (roleInfo) {
      document.getElementById("career-detail-role-title").textContent = roleInfo.title;
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

    const compareList = document.getElementById("career-multi-role-list");
    if (compareList) {
      compareList.innerHTML = comparisons.map(c => `
        <div class="action-card-item">
          <div class="action-card-header">
            <span class="action-skill-title">${c.role_title}</span>
            <span class="badge ${c.is_job_ready ? 'badge-diff' : 'badge-cyan'}">${c.suitability_score}% Suitability</span>
          </div>
          <p class="action-desc">${c.explanation}</p>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Career view error:", err);
  }
}

async function changeTargetRole(newRole) {
  if (state.currentUser) {
    state.currentUser.target_role = newRole;
    updateUserWidget();
    try {
      await fetch(`${API_BASE}/career/set-target?role_id=${newRole}`, {
        method: "POST",
        headers: getAuthHeaders()
      });
      await loadCareerView();
      await refreshDashboard();
    } catch (err) {
      console.error("Change role error:", err);
    }
  }
}

// ==================== ADAPTIVE ASSESSMENT CONTROLLER ====================
async function startNewAssessment(questionCount = 10) {
  switchView("assessment");

  try {
    const res = await fetch(`${API_BASE}/assessment/generate?total_questions=${questionCount}`, {
      method: "POST",
      headers: getAuthHeaders()
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
    console.error("Error launching test:", err);
  }
}

function renderQuestion() {
  const { questions, currentIndex } = state.currentAssessment;
  if (!questions || questions.length === 0) return;

  const q = questions[currentIndex];

  document.getElementById("test-skill-badge").textContent = q.skill;
  document.getElementById("test-concept-badge").textContent = q.concept;
  document.getElementById("test-diff-badge").textContent = `Diff ${q.difficulty}/5`;
  document.getElementById("current-q-index").textContent = currentIndex + 1;
  document.getElementById("total-q-count").textContent = questions.length;

  const progressPct = ((currentIndex + 1) / questions.length) * 100;
  document.getElementById("assessment-progress-fill").style.width = `${progressPct}%`;

  document.getElementById("q-subtopic-text").textContent = `Subtopic: ${q.subtopic || q.concept}`;
  document.getElementById("question-text").textContent = q.question;

  const reasonEl = document.getElementById("q-selection-reason-text");
  if (reasonEl) {
    reasonEl.textContent = q.selection_reason || "Selected based on Fisher information optimization and mastery targeting.";
  }

  const container = document.getElementById("options-container");
  container.innerHTML = q.options.map((opt, idx) => `
    <button class="option-btn" id="opt-btn-${idx}" onclick="selectOption(${idx})">
      <div class="opt-index">${String.fromCharCode(65 + idx)}</div>
      <div class="opt-text">${opt}</div>
    </button>
  `).join("");

  document.getElementById("answer-feedback-box").classList.add("hidden");
  document.getElementById("btn-next-question").classList.add("hidden");
}

async function selectOption(chosenIdx) {
  const { questions, currentIndex } = state.currentAssessment;
  const q = questions[currentIndex];

  const optionButtons = document.querySelectorAll(".option-btn");
  optionButtons.forEach(btn => btn.disabled = true);

  state.currentAssessment.answers.push({
    question_id: q.id,
    selected_option: chosenIdx
  });

  try {
    const submitRes = await fetch(`${API_BASE}/assessment/submit`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        target_role: state.currentUser.target_role,
        submissions: [{ question_id: q.id, selected_option: chosenIdx }]
      })
    });

    if (submitRes.ok) {
      const respData = await submitRes.json();
      const answerRes = respData.results[0];

      const chosenBtn = document.getElementById(`opt-btn-${chosenIdx}`);
      const correctBtn = document.getElementById(`opt-btn-${answerRes.correct_option}`);

      if (answerRes.is_correct) {
        if (chosenBtn) chosenBtn.classList.add("selected-correct");
      } else {
        if (chosenBtn) chosenBtn.classList.add("selected-wrong");
        if (correctBtn) correctBtn.classList.add("selected-correct");
      }

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

      const nextBtn = document.getElementById("btn-next-question");
      nextBtn.classList.remove("hidden");
      if (currentIndex === questions.length - 1) {
        nextBtn.innerHTML = `<span>View Psychometric Results</span> <i class="fa-solid fa-award"></i>`;
      } else {
        nextBtn.innerHTML = `<span>Next Question</span> <i class="fa-solid fa-arrow-right"></i>`;
      }
    }
  } catch (err) {
    console.error("Submit question error:", err);
  }
}

function nextQuestion() {
  const { questions, currentIndex } = state.currentAssessment;
  if (currentIndex < questions.length - 1) {
    state.currentAssessment.currentIndex += 1;
    renderQuestion();
  } else {
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

    const container = document.getElementById("results-mastery-list");
    if (container && data.skills) {
      container.innerHTML = data.skills.map(s => `
        <div class="breakdown-item">
          <span class="b-concept">${s.skill_name}</span>
          <span class="b-delta text-cyan">${s.descriptive_level} (${Math.round(s.numeric_mastery * 100)}%)</span>
        </div>
      `).join("");
    }
  }
}

// ==================== AUTH CONTROLLER ====================
function openAuthModal(mode = "login") {
  state.authMode = mode;
  const modal = document.getElementById("auth-modal");
  const title = document.getElementById("auth-modal-title");
  const nameGroup = document.getElementById("auth-name-group");
  const submitBtn = document.getElementById("btn-auth-submit");
  const toggleText = document.getElementById("auth-toggle-text");
  const toggleBtn = document.getElementById("btn-toggle-auth-mode");

  if (mode === "login") {
    title.innerHTML = `<i class="fa-solid fa-shield-halved text-cyan"></i> Account Sign In`;
    nameGroup.classList.add("hidden");
    submitBtn.innerHTML = `<span>Sign In</span> <i class="fa-solid fa-arrow-right"></i>`;
    toggleText.textContent = "Don't have an account?";
    toggleBtn.textContent = "Create one";
  } else {
    title.innerHTML = `<i class="fa-solid fa-user-plus text-indigo"></i> Create Student Account`;
    nameGroup.classList.remove("hidden");
    submitBtn.innerHTML = `<span>Create Account</span> <i class="fa-solid fa-arrow-right"></i>`;
    toggleText.textContent = "Already have an account?";
    toggleBtn.textContent = "Sign in";
  }

  document.getElementById("auth-error-display").classList.add("hidden");
  modal.classList.remove("hidden");
}

function closeAuthModal() {
  document.getElementById("auth-modal").classList.add("hidden");
}

function toggleAuthMode() {
  openAuthModal(state.authMode === "login" ? "register" : "login");
}

async function submitAuthForm(e) {
  e.preventDefault();
  const errBox = document.getElementById("auth-error-display");
  errBox.classList.add("hidden");

  const email = document.getElementById("auth-input-email").value;
  const password = document.getElementById("auth-input-password").value;
  const name = document.getElementById("auth-input-name").value;

  const endpoint = state.authMode === "login" ? `${API_BASE}/auth/login` : `${API_BASE}/auth/register`;
  const body = state.authMode === "login" ? { email, password } : { name, email, password, target_role: "data_scientist" };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    if (res.ok) {
      const data = await res.json();
      state.token = data.access_token;
      state.currentUser = data.user;
      localStorage.setItem("synapsecat_jwt", state.token);
      closeAuthModal();
      await initializeAuthenticatedSession();
    } else {
      const err = await res.json();
      errBox.textContent = err.detail || "Authentication failed. Please check credentials.";
      errBox.classList.remove("hidden");
    }
  } catch (err) {
    errBox.textContent = "Network error. Please try again.";
    errBox.classList.remove("hidden");
  }
}

async function handleOAuthLogin(provider) {
  try {
    const mockCode = `auth_${provider}_token_${Date.now()}`;
    const res = await fetch(`${API_BASE}/auth/oauth/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: provider, code: mockCode })
    });

    if (res.ok) {
      const data = await res.json();
      state.token = data.access_token;
      state.currentUser = data.user;
      localStorage.setItem("synapsecat_jwt", state.token);
      closeAuthModal();
      await initializeAuthenticatedSession();
    }
  } catch (err) {
    console.error("OAuth callback error:", err);
  }
}

function handleLogout() {
  state.token = null;
  state.currentUser = null;
  localStorage.removeItem("synapsecat_jwt");
  openAuthModal("login");
}

// ==================== ONBOARDING CONTROLLER ====================
function openOnboardingModal() {
  document.getElementById("onboarding-modal").classList.remove("hidden");
}

function closeOnboardingModal() {
  document.getElementById("onboarding-modal").classList.add("hidden");
}

async function submitOnboardingForm(e) {
  e.preventDefault();
  const education = document.getElementById("onb-education").value;
  const gradYear = parseInt(document.getElementById("onb-grad-year").value);
  const targetRole = document.getElementById("onb-target-role").value;

  const skillSelects = document.querySelectorAll(".skill-rate-row .s-level");
  const techSkills = Array.from(skillSelects).map(sel => ({
    name: sel.getAttribute("data-skill"),
    level: sel.value
  }));

  try {
    const res = await fetch(`${API_BASE}/onboarding/submit`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        education_level: education,
        major: "Computer Science",
        graduation_year: gradYear,
        experience_level: "Beginner / Student",
        placement_goal: `Campus Placements ${gradYear}`,
        target_role: targetRole,
        technical_skills: techSkills,
        soft_skills: ["Problem Solving", "Communication"],
        preferred_technologies: ["Python", "SQL", "FastAPI"]
      })
    });

    if (res.ok) {
      closeOnboardingModal();
      if (state.currentUser) {
        state.currentUser.onboarding_completed = true;
        state.currentUser.target_role = targetRole;
      }
      updateUserWidget();
      await refreshDashboard();
      switchView("dashboard");
    }
  } catch (err) {
    console.error("Onboarding submission error:", err);
  }
}
