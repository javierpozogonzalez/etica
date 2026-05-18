const $app = document.getElementById("app");

let data = null;
let session = null;

async function loadData() {
  const res = await fetch("data/questions.json");
  if (!res.ok) throw new Error("No se pudo cargar el banco de preguntas");
  return res.json();
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function pickQuestions({ tema = null, count = null }) {
  let pool = data.questions;
  if (tema != null) pool = pool.filter((q) => q.tema === tema);
  pool = shuffle(pool);
  if (count != null) pool = pool.slice(0, Math.min(count, pool.length));
  return pool;
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function renderHome() {
  const { meta } = data;
  $app.innerHTML = `
    <div class="panel">
      <h2>Elige modo de práctica</h2>
      <p class="lead">${meta.totalQuestions} preguntas repartidas en ${meta.temas.length} temas. Simula el examen con ${meta.examSize} preguntas aleatorias.</p>
      <div class="mode-grid">
        <button type="button" class="mode-card featured" data-mode="exam">
          <strong>Simulacro de examen</strong>
          <span>${meta.examSize} preguntas aleatorias de todos los temas</span>
        </button>
        <button type="button" class="mode-card" data-mode="random">
          <strong>Preguntas aleatorias</strong>
          <span>Elige cuántas preguntas quieres practicar</span>
        </button>
        <button type="button" class="mode-card" data-mode="tema">
          <strong>Por tema</strong>
          <span>Estudia un bloque temático concreto</span>
        </button>
      </div>
    </div>
    <div class="panel hidden" id="tema-panel">
      <h2>Selecciona un tema</h2>
      <p class="lead">Practica todas las preguntas del tema o un subconjunto aleatorio.</p>
      <div class="tema-list">
        ${meta.temas
          .map(
            (t) => `
          <button type="button" class="tema-btn" data-tema="${t.id}">
            <span><strong>Tema ${t.id}.</strong> ${escapeHtml(t.name)}</span>
            <span class="count">${t.count} preg.</span>
          </button>`
          )
          .join("")}
      </div>
    </div>
    <div class="panel hidden" id="count-panel">
      <h2>¿Cuántas preguntas?</h2>
      <p class="lead">Introduce un número entre 5 y ${meta.totalQuestions}.</p>
      <div class="actions">
        <input type="number" id="q-count" min="5" max="${meta.totalQuestions}" value="20"
          style="padding:0.75rem 1rem;border-radius:10px;border:1px solid var(--border);background:var(--surface-2);color:var(--text);font-size:1rem;width:120px;font-family:inherit" />
        <button type="button" class="btn btn-primary" id="start-count">Empezar</button>
      </div>
    </div>
  `;

  $app.querySelector('[data-mode="exam"]').addEventListener("click", () => {
    startSession({
      title: "Simulacro de examen",
      subtitle: `${meta.examSize} preguntas aleatorias`,
      questions: pickQuestions({ count: meta.examSize }),
    });
  });

  $app.querySelector('[data-mode="random"]').addEventListener("click", () => {
    document.getElementById("count-panel").classList.remove("hidden");
    document.getElementById("tema-panel").classList.add("hidden");
    session = { mode: "random" };
  });

  $app.querySelector('[data-mode="tema"]').addEventListener("click", () => {
    document.getElementById("tema-panel").classList.remove("hidden");
    document.getElementById("count-panel").classList.add("hidden");
  });

  $app.querySelectorAll(".tema-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const temaId = Number(btn.dataset.tema);
      const tema = meta.temas.find((t) => t.id === temaId);
      const all = pickQuestions({ tema: temaId });
      startSession({
        title: `Tema ${temaId}`,
        subtitle: tema.name,
        questions: all,
      });
    });
  });

  document.getElementById("start-count").addEventListener("click", () => {
    const n = Number(document.getElementById("q-count").value);
    if (n < 5 || n > meta.totalQuestions) {
      alert(`Introduce un número entre 5 y ${meta.totalQuestions}`);
      return;
    }
    startSession({
      title: "Práctica aleatoria",
      subtitle: `${n} preguntas`,
      questions: pickQuestions({ count: n }),
    });
  });
}

function startSession({ title, subtitle, questions }) {
  session = {
    title,
    subtitle,
    questions,
    index: 0,
    answers: [],
    revealed: false,
    selected: null,
    finished: false,
  };
  renderQuiz();
}

function currentQ() {
  return session.questions[session.index];
}

function renderQuiz() {
  if (session.finished) {
    renderResults();
    return;
  }

  const q = currentQ();
  const total = session.questions.length;
  const pct = Math.round(((session.index) / total) * 100);

  $app.innerHTML = `
    <button type="button" class="back-link" id="btn-home">← Volver al inicio</button>
    <div class="quiz-header">
      <div class="quiz-meta">
        <span class="badge accent">${escapeHtml(session.title)}</span>
        <span class="badge">${escapeHtml(session.subtitle)}</span>
      </div>
      <div class="progress-wrap">
        <div class="progress-label">
          <span>Pregunta ${session.index + 1} de ${total}</span>
          <span>${pct}%</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      </div>
    </div>
    <div class="panel">
      <p class="badge" style="margin-bottom:0.75rem">Tema ${q.tema} · nº ${q.number}</p>
      <p class="question-text">${escapeHtml(q.question)}</p>
      <div class="options" id="options">
        ${q.options
          .map(
            (o) => `
          <button type="button" class="option" data-key="${o.key}" ${session.revealed ? "disabled" : ""}>
            <span class="option-key">${o.key}</span>
            <span>${escapeHtml(o.text)}</span>
          </button>`
          )
          .join("")}
      </div>
      <div id="explanation-slot"></div>
      <div class="actions">
        <button type="button" class="btn btn-primary" id="btn-reveal" ${session.revealed ? "disabled" : ""}>
          Ver respuesta
        </button>
        <button type="button" class="btn btn-secondary hidden" id="btn-next">
          ${session.index + 1 >= total ? "Ver resultados" : "Siguiente pregunta"}
        </button>
      </div>
    </div>
  `;

  document.getElementById("btn-home").addEventListener("click", () => {
    if (confirm("¿Salir de la sesión actual?")) renderHome();
  });

  const optionsEl = document.getElementById("options");
  optionsEl.querySelectorAll(".option").forEach((btn) => {
    btn.addEventListener("click", () => selectOption(btn.dataset.key));
  });

  document.getElementById("btn-reveal").addEventListener("click", revealAnswer);
  document.getElementById("btn-next").addEventListener("click", nextQuestion);

  if (session.revealed) applyRevealStyles();
  if (session.selected) highlightSelected(session.selected);
}

function selectOption(key) {
  if (session.revealed) return;
  session.selected = key;
  highlightSelected(key);
}

function highlightSelected(key) {
  document.querySelectorAll(".option").forEach((btn) => {
    btn.classList.toggle("selected", btn.dataset.key === key);
  });
}

function revealAnswer() {
  if (!session.revealed) {
    session.revealed = true;
    const q = currentQ();
    const chosen = session.selected;
    const correct = q.correct === chosen;

    session.answers.push({
      questionId: q.id,
      chosen: chosen ?? null,
      correct: q.correct,
      isCorrect: chosen != null && correct,
    });

    applyRevealStyles();

    const slot = document.getElementById("explanation-slot");
    slot.innerHTML = `
      <div class="explanation">
        <h3>Respuesta correcta: ${q.correct.toUpperCase()}</h3>
        <p>${escapeHtml(q.explanation)}</p>
      </div>
    `;

    document.getElementById("btn-reveal").disabled = true;
    document.getElementById("btn-next").classList.remove("hidden");
  }
}

function applyRevealStyles() {
  const q = currentQ();
  document.querySelectorAll(".option").forEach((btn) => {
    const key = btn.dataset.key;
    btn.disabled = true;
    btn.classList.remove("selected");
    if (key === q.correct) btn.classList.add("correct");
    else if (key === session.selected) btn.classList.add("incorrect");
  });
}

function nextQuestion() {
  if (session.index + 1 >= session.questions.length) {
    session.finished = true;
    renderResults();
    return;
  }
  session.index += 1;
  session.revealed = false;
  session.selected = null;
  renderQuiz();
}

function renderResults() {
  const total = session.answers.length;
  const ok = session.answers.filter((a) => a.isCorrect).length;
  const unanswered = session.answers.filter((a) => a.chosen == null).length;
  const ko = total - ok - unanswered;
  const pct = total ? Math.round((ok / total) * 100) : 0;

  $app.innerHTML = `
    <button type="button" class="back-link" id="btn-home">← Volver al inicio</button>
    <div class="panel">
      <h2>Resultados</h2>
      <p class="lead">${escapeHtml(session.title)} — ${escapeHtml(session.subtitle)}</p>
      <div class="score-ring">
        <div class="score-value">${pct}%</div>
        <p class="score-label">${ok} aciertos de ${total} preguntas</p>
      </div>
      <div class="stats-grid">
        <div class="stat-box ok"><div class="num">${ok}</div><div class="lbl">Correctas</div></div>
        <div class="stat-box ko"><div class="num">${ko}</div><div class="lbl">Incorrectas</div></div>
        <div class="stat-box"><div class="num">${unanswered}</div><div class="lbl">Sin responder</div></div>
      </div>
      <div class="actions">
        <button type="button" class="btn btn-primary" id="btn-retry">Repetir misma sesión</button>
        <button type="button" class="btn btn-secondary" id="btn-new">Nueva sesión</button>
      </div>
    </div>
  `;

  document.getElementById("btn-home").addEventListener("click", renderHome);
  document.getElementById("btn-new").addEventListener("click", renderHome);
  document.getElementById("btn-retry").addEventListener("click", () => {
    const qs = shuffle(session.questions);
    startSession({
      title: session.title,
      subtitle: session.subtitle,
      questions: qs,
    });
  });
}

async function init() {
  $app.innerHTML = `<div class="panel"><p class="lead">Cargando banco de preguntas…</p></div>`;
  try {
    data = await loadData();
    renderHome();
  } catch (e) {
    $app.innerHTML = `<div class="panel"><p class="lead">Error: ${escapeHtml(e.message)}. Abre la web con un servidor local (p. ej. <code>python -m http.server</code>).</p></div>`;
  }
}

init();
