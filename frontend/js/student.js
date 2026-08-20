const studentId = localStorage.getItem("student_id");
const studentName = localStorage.getItem("student_name");

if (!studentId) {
  window.location.href = "join.html";
}

document.getElementById("studentHeading").textContent = studentName || "Student";

function showErr(msg) {
  const err = document.getElementById("err");
  err.textContent = msg;
  err.style.display = "block";
}
function clearErr() {
  document.getElementById("err").style.display = "none";
}

async function loadAndRender() {
  try {
    const state = await api.get(`/api/student/${studentId}/state`);
    document.getElementById("sessionInfo").textContent = `${state.session.name}`;
    if (state.is_final) {
      const summary = await api.get(`/api/student/${studentId}/summary`);
      renderFinal(state, summary);
    } else {
      renderWorkspace(state);
    }
  } catch (e) {
    showErr(e.message);
  }
}

function scenarioBlock(state) {
  const facts = state.scenario.company_facts.map(f => `<li>${escapeHtml(f)}</li>`).join("");
  const checklist = state.characteristics.map(c => `<li>${escapeHtml(c)}</li>`).join("");
  return `
    <div class="card">
      <h2>The scenario</h2>
      <p><strong>${escapeHtml(state.scenario.company)}</strong> is entering the US pizza market.</p>
      <p>${escapeHtml(state.scenario.market_landscape)}</p>
      <ul>${facts}</ul>
    </div>
    <div class="card">
      <h2>The 5 required characteristics</h2>
      <p class="muted">Your mission statement needs to satisfy all five:</p>
      <ul class="checklist">${checklist}</ul>
      <p class="wordcount">Guideline: aim for under ~${state.word_count_guideline} words.</p>
    </div>
  `;
}

function criteriaList(criteria) {
  return criteria.map(c => `
    <div class="criteria-item">
      <div class="crit-head">
        <span>${escapeHtml(c.characteristic)}</span>
        <span class="pill ${c.status === 'Pass' ? 'pass' : 'needswork'}">${c.status}</span>
      </div>
      <p>${escapeHtml(c.feedback)}</p>
    </div>
  `).join("");
}

function personaGrid(personas) {
  return `<div class="persona-grid">
    ${Object.values(personas).map(p => `
      <div class="persona-card">
        <div class="persona-label">${escapeHtml(p.label)}</div>
        <div class="persona-lens">${escapeHtml(p.lens)}</div>
        <p>${escapeHtml(p.reaction)}</p>
      </div>
    `).join("")}
  </div>`;
}

function feedbackCard(attempt, title) {
  return `
    <div class="card">
      <h2>${title}</h2>
      <p class="muted">"${escapeHtml(attempt.draft_text)}"</p>
      <p class="wordcount">${attempt.word_count} words ${attempt.word_count > 20 ? "&mdash; over the ~20 word guideline" : ""}</p>
      <h3 style="margin-top:16px">Department reactions</h3>
      ${personaGrid(attempt.persona_reactions)}
      <h3 style="margin-top:16px">Criteria checklist</h3>
      ${criteriaList(attempt.criteria_result)}
    </div>
  `;
}

function renderWorkspace(state) {
  clearErr();
  const main = document.getElementById("main");
  const attempts = state.attempts;
  const latest = attempts.length ? attempts[attempts.length - 1] : null;

  let html = scenarioBlock(state);

  if (latest) {
    html += feedbackCard(latest, `Attempt ${latest.attempt_number} feedback`);
    html += `
      <div class="card">
        <p>Happy with this version?</p>
        <div class="btn-row">
          <button id="finalizeBtn">Submit this as my final answer</button>
        </div>
      </div>
    `;
  }

  if (state.attempts_remaining > 0) {
    html += `
      <div class="card">
        <h2>${latest ? "Revise your draft" : "Write your draft"}</h2>
        <p class="muted">Attempt ${attempts.length + 1} of ${state.session.max_attempts}</p>
        <label for="draft">Mission statement draft</label>
        <textarea id="draft">${latest ? escapeHtml(latest.draft_text) : ""}</textarea>
        <button id="getFeedbackBtn">Get feedback</button>
      </div>
    `;
  } else if (!latest) {
    html += `<div class="card"><p class="muted">No attempts remaining.</p></div>`;
  }

  if (attempts.length > 1) {
    html += `
      <div class="card">
        <h2>Previous attempts</h2>
        <ul class="attempt-history">
          ${attempts.slice(0, -1).map(a => `<li><strong>Attempt ${a.attempt_number}:</strong> "${escapeHtml(a.draft_text)}" <span class="muted">(${a.word_count} words)</span></li>`).join("")}
        </ul>
      </div>
    `;
  }

  main.innerHTML = html;

  const feedbackBtn = document.getElementById("getFeedbackBtn");
  if (feedbackBtn) {
    feedbackBtn.addEventListener("click", async (e) => {
      const draftText = document.getElementById("draft").value.trim();
      if (!draftText) return showErr("Please write a draft first.");
      e.target.disabled = true;
      e.target.textContent = "Getting feedback from the review panel…";
      try {
        await api.post(`/api/student/${studentId}/attempts`, { draft_text: draftText });
        await loadAndRender();
      } catch (err) {
        showErr(err.message);
        e.target.disabled = false;
        e.target.textContent = "Get feedback";
      }
    });
  }

  const finalizeBtn = document.getElementById("finalizeBtn");
  if (finalizeBtn) {
    finalizeBtn.addEventListener("click", async (e) => {
      if (!confirm("Submit this as your final answer? You won't be able to revise after this.")) return;
      e.target.disabled = true;
      try {
        await api.post(`/api/student/${studentId}/finalize`, { attempt_number: latest.attempt_number });
        await loadAndRender();
      } catch (err) {
        showErr(err.message);
        e.target.disabled = false;
      }
    });
  }
}

function renderFinal(state, summary) {
  clearErr();
  const main = document.getElementById("main");
  const final = summary.final_attempt;

  let html = `
    <div class="card">
      <h2>Final submission &mdash; ${escapeHtml(summary.student_name)}</h2>
      <p class="muted">${escapeHtml(summary.session_name)}</p>
      <div class="btn-row"><button class="secondary" onclick="window.print()">Print / save as PDF</button></div>
    </div>
    <div class="card">
      <h2>All attempts</h2>
      <ul class="attempt-history">
        ${summary.attempts.map(a => `<li><strong>Attempt ${a.attempt_number}${a.is_final ? " (final)" : ""}:</strong> "${escapeHtml(a.draft_text)}" <span class="muted">(${a.word_count} words)</span></li>`).join("")}
      </ul>
    </div>
  `;
  html += feedbackCard(final, "Final version &mdash; department reactions & criteria checklist");

  main.innerHTML = html;
}

loadAndRender();
