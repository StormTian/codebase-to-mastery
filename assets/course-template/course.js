(() => {
  const modules = [...document.querySelectorAll('.course-module')];
  const dots = [...document.querySelectorAll('.nav-dot')];
  const progress = document.querySelector('#progress-bar');
  const systemReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let userReducedMotion = false;
  try { userReducedMotion = localStorage.getItem('code-learning:reduce-motion') === 'true'; } catch (_) {}
  let reduceMotion = systemReducedMotion || userReducedMotion;
  const motionToggle = document.querySelector('#motion-toggle');
  const applyMotion = () => {
    reduceMotion = systemReducedMotion || userReducedMotion;
    document.documentElement.dataset.reducedMotion = String(reduceMotion);
    if (motionToggle) {
      motionToggle.setAttribute('aria-pressed', String(reduceMotion));
      motionToggle.disabled = systemReducedMotion;
    }
  };
  applyMotion();
  motionToggle?.addEventListener('click', () => {
    userReducedMotion = !userReducedMotion;
    try { localStorage.setItem('code-learning:reduce-motion', String(userReducedMotion)); } catch (_) {}
    applyMotion();
  });

  let activeModuleId;
  const setActiveModule = (id) => {
    if (activeModuleId === id) return;
    activeModuleId = id;
    dots.forEach((dot) => {
      const active = dot.dataset.target === id;
      dot.classList.toggle('is-active', active);
      if (active) dot.setAttribute('aria-current', 'step');
      else dot.removeAttribute('aria-current');
      const nav = dot.parentElement;
      if (active && nav.scrollWidth > nav.clientWidth) {
        nav.scrollTo({ left: dot.offsetLeft - nav.offsetLeft - (nav.clientWidth - dot.offsetWidth) / 2,
          behavior: reduceMotion ? 'auto' : 'smooth' });
      }
    });
  };

  dots.forEach((dot) => {
    dot.addEventListener('click', () => {
      document.getElementById(dot.dataset.target)?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  });

  const updateProgress = () => {
    const available = document.documentElement.scrollHeight - window.innerHeight;
    const ratio = available > 0 ? Math.min(1, Math.max(0, window.scrollY / available)) : 0;
    if (progress) progress.style.width = `${ratio * 100}%`;
    const current = currentModuleIndex();
    if (modules.length) setActiveModule(current >= 0 ? modules[current].id : null);
  };
  document.addEventListener('scroll', updateProgress, { passive: true });

  const currentModuleIndex = () => {
    const center = window.scrollY + window.innerHeight * 0.45;
    let best = -1;
    modules.forEach((module, index) => {
      if (module.offsetTop <= center) best = index;
    });
    return best;
  };
  updateProgress();

  document.addEventListener('keydown', (event) => {
    if (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(document.activeElement?.tagName)) return;
    const forward = event.key === 'j' || event.key === 'J' || event.key === 'ArrowDown';
    const backward = event.key === 'k' || event.key === 'K' || event.key === 'ArrowUp';
    if (!forward && !backward) return;
    const offset = forward ? 1 : -1;
    const target = modules[Math.min(modules.length - 1, Math.max(0, currentModuleIndex() + offset))];
    if (target) {
      event.preventDefault();
      target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth' });
    }
  });

  document.querySelectorAll('dfn[data-definition]').forEach((term) => {
    term.tabIndex = 0;
    term.setAttribute('aria-label', `${term.textContent}: ${term.dataset.definition}`);
  });

  document.querySelectorAll('.code-translation').forEach((translation) => {
    const label = translation.querySelector('.source-label');
    if (label) {
      const range = (translation.dataset.lines || '').replace('-', '–');
      label.textContent = `Real code · ${translation.dataset.source || 'unknown source'}:${range}`;
    }
  });

  document.querySelectorAll('.quiz').forEach((quiz) => {
    const choices = [...quiz.querySelectorAll('.quiz-options button')];
    const feedback = quiz.querySelector('.quiz-feedback');
    choices.forEach((choice) => {
      choice.addEventListener('click', () => {
        choices.forEach((item) => item.classList.remove('is-correct', 'is-wrong'));
        const correct = choice.dataset.correct === 'true';
        choice.classList.add(correct ? 'is-correct' : 'is-wrong');
        feedback.textContent = `${correct ? 'Exactly. ' : 'Not quite. '}${quiz.dataset.explanation || ''}`;
      });
    });
  });

  const playChat = (chat) => {
    const messages = [...chat.querySelectorAll('.chat-message')];
    messages.forEach((message) => message.classList.remove('is-visible'));
    messages.forEach((message, index) => {
      if (reduceMotion) message.classList.add('is-visible');
      else window.setTimeout(() => message.classList.add('is-visible'), 180 + index * 520);
    });
  };

  document.querySelectorAll('.component-chat').forEach((chat) => {
    playChat(chat);
    chat.querySelector('.replay-chat')?.addEventListener('click', () => playChat(chat));
  });

  document.querySelectorAll('.data-flow').forEach((flow) => {
    const steps = [...flow.querySelectorAll('.flow-step')];
    const detail = flow.querySelector('.flow-detail');
    steps.forEach((step) => {
      step.addEventListener('click', () => {
        steps.forEach((item) => item.classList.remove('is-active'));
        step.classList.add('is-active');
        if (detail) detail.textContent = step.dataset.detail || '';
      });
    });
  });

  const panel = document.querySelector('.learning-panel');
  if (panel) {
    const storageKey = `code-learning:${panel.dataset.kitId}`;
    const sourceRevision = document.querySelectorAll('.course-meta dd')[1]?.textContent || 'unknown';
    const feedback = panel.querySelector('.notes-feedback');
    const zh = document.documentElement.lang.startsWith('zh');
    let notes = {};
    try { notes = JSON.parse(localStorage.getItem(storageKey) || '{}'); } catch (_) { notes = {}; }
    if (!notes || typeof notes !== 'object' || Array.isArray(notes)) notes = {};
    panel.querySelectorAll('.recall').forEach((recall) => {
      const field = recall.querySelector('textarea');
      const key = recall.dataset.recallId;
      field.value = typeof notes[key]?.response === 'string' ? notes[key].response : '';
      field.addEventListener('input', () => {
        notes[key] = { response: field.value, sourceRevision, recordedAt: new Date().toISOString(), kind: 'provisional-recall' };
        try {
          localStorage.setItem(storageKey, JSON.stringify(notes));
          if (feedback) feedback.textContent = zh ? '回忆已保存到本机浏览器；尚未评价掌握程度。' : 'Recall saved in this browser; mastery has not been assessed.';
        } catch (_) {
          if (feedback) feedback.textContent = zh ? '浏览器未允许保存；可导出本次记录。' : 'Browser storage is unavailable; export this session to keep it.';
        }
      });
    });
    let exportURL;
    panel.querySelector('.export-learning-notes')?.addEventListener('click', () => {
      const content = { kitId: panel.dataset.kitId, sourceRevision, assessment: 'unassessed', notes };
      const text = JSON.stringify(content, null, 2);
      const preview = panel.querySelector('.export-preview');
      if (preview) {
        preview.hidden = false;
        preview.open = true;
        preview.querySelector('textarea').value = text;
        if (exportURL) URL.revokeObjectURL(exportURL);
        exportURL = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
        preview.querySelector('.export-download').href = exportURL;
        if (feedback) feedback.textContent = zh ? '记录已准备好：可以下载 JSON，或从下方文本框复制。' : 'Records are ready: download JSON or copy the text below.';
      }
    });
    window.addEventListener('pagehide', () => { if (exportURL) URL.revokeObjectURL(exportURL); });
  }
})();
