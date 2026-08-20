let currentCode = localStorage.getItem("instructor_session_code") || "";

function showErr(msg) {
  const err = document.getElementById("err");
  err.textContent = msg;
  err.style.display = "block";
}
function clearErr() {
  document.getElementById("err").style.display = "none";
}

document.getElementById("createBtn").addEventListener("click", async () => {
  clearErr();
  const name = document.getElementById("sName").value.trim();
  if (!name) return showErr("Assignment name is required.");
  const max_attempts = parseInt(document.getElementById("sAttempts").value) || 3;
  try {
    const data = await api.post("/api/instructor/sessions", { name, max_attempts });
    currentCode = data.session.code;
    localStorage.setItem("instructor_session_code", currentCode);
    renderDashboard(data);
  } catch (e) {
    showErr(e.message);
  }
});

document.getElementById("loadBtn").addEventListener("click", async () => {
  clearErr();
  const code = document.getElementById("loadCode").value.trim().toUpperCase();
  if (!code) return showErr("Enter an assignment code.");
  await loadSession(code);
});

async function loadSession(code) {
  try {
    const data = await api.get(`/api/instructor/sessions/${code}`);
    currentCode = code;
    localStorage.setItem("instructor_session_code", code);
    renderDashboard(data);
  } catch (e) {
    showErr(e.message);
  }
}

async function refresh() {
  if (!currentCode) return;
  try {
    const data = await api.get(`/api/instructor/sessions/${currentCode}`);
    renderDashboard(data);
  } catch (e) {
    // ignore transient poll errors
  }
}

function renderDashboard(data) {
  document.getElementById("dashboard").style.display = "block";
  const { session, students, finalized_count, struggle_stats } = data;

  let html = `
    <div class="card">
      <div class="row">
        <div>
          <h3>Assignment</h3>
          <h2>${escapeHtml(session.name)}</h2>
          <p class="muted">Share this code with students to join:</p>
          <div style="font-size:1.8rem;font-weight:800;letter-spacing:0.1em">${session.code}</div>
          <p class="muted" style="margin-top:8px">Max attempts: ${session.max_attempts}</p>
        </div>
        <div>
          <h3>Progress</h3>
          <p>${students.length} student${students.length === 1 ? "" : "s"} joined</p>
          <p>${finalized_count} finalized submission${finalized_count === 1 ? "" : "s"}</p>
          <a href="/api/instructor/sessions/${session.code}/export.csv"><button class="secondary" type="button">Export to CSV</button></a>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>Where students struggled (finalized submissions)</h2>
      ${finalized_count === 0 ? `<p class="muted">No finalized submissions yet.</p>` : `
        <ul class="checklist">
          ${struggle_stats.map(s => `<li>${escapeHtml(s.characteristic)} &mdash; <strong>${fmtPct(s.needs_work_rate)}</strong> needed work (${s.needs_work_count}/${finalized_count})</li>`).join("")}
        </ul>
      `}
    </div>

    <div class="card">
      <h2>Students</h2>
      <table>
        <thead><tr><th>Name</th><th>Attempts used</th><th>Status</th><th>Final word count</th></tr></thead>
        <tbody>
          ${students.length === 0 ? `<tr><td colspan="4" class="muted">No students have joined yet.</td></tr>` : ""}
          ${students.map(s => `<tr>
            <td>${escapeHtml(s.student_name)}</td>
            <td>${s.attempts_used} / ${session.max_attempts}</td>
            <td>${s.is_final ? `<span class="pill final">Finalized</span>` : `<span class="pill">In progress</span>`}</td>
            <td>${s.final_word_count !== null && s.final_word_count !== undefined ? s.final_word_count : "-"}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>
  `;

  document.getElementById("dashboard").innerHTML = html;
}

if (currentCode) {
  document.getElementById("loadCode").value = currentCode;
  loadSession(currentCode);
}
setInterval(refresh, 6000);
