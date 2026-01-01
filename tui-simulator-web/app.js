const output = document.querySelector('#log-lines');
const statusLine = document.querySelector('#status-line');
const statusVerbEl = statusLine?.querySelector('.status-verb');
const statusInfoEl = statusLine?.querySelector('.status-info');
const statusTimerEl = statusLine?.querySelector('.status-timer');
const statusIconEl = statusLine?.querySelector('.status-icon');
const frame = document.querySelector('.terminal-frame');
const promptForm = document.querySelector('#prompt-form');
const promptInput = document.querySelector('#prompt-input');

let logSnapshot = null;
const STATUS_PRESETS = {
  idle: {
    verbs: ['Staring into void', 'Buffering vibes', 'Awaiting cue'],
    info: '— gaidu jautājumu.',
    iconClass: 'state-idle',
  },
  busy: {
    verbs: ['Herding cats', 'Untangling thoughts', 'Synth-ing reply'],
    info: 'Interpretēju straumi · Esc lai pārtrauktu',
    iconClass: 'state-busy',
  },
  tool: {
    verbs: ['Rifling archives', 'Poking APIs', 'Fishing packets'],
    info: 'search-events + list-events (2w window)',
    iconClass: 'state-tool',
  },
};

const statusController = {
  state: 'idle',
  verbs: [],
  verbIndex: 0,
  verbHandle: null,
  timerHandle: null,
  timerStartedAt: null,
};
const audioController = {
  ctx: null,
  oscillator: null,
  gain: null,
  enabled: true,
  total: 0,
};
const groupingState = {
  assistantPartial: {
    node: null,
    count: 0,
    lastText: '',
  },
  userMessage: {
    node: null,
    collapsed: false,
    label: '',
  },
};

function appendLine({ type = '', text, element }) {
  const container = document.createElement('div');
  container.className = `line ${type}`.trim();

  if (element) {
    container.appendChild(element);
  } else if (text) {
    container.textContent = text;
  }

  output.appendChild(container);
  output.scrollTop = output.scrollHeight;
  return container;
}

function setStatusVerb(text) {
  if (!statusVerbEl) return;
  statusVerbEl.textContent = text;
  statusVerbEl.classList.remove('swap');
  void statusVerbEl.offsetWidth;
  statusVerbEl.classList.add('swap');
  setTimeout(() => statusVerbEl.classList.remove('swap'), 400);
}

function startVerbRotation(words = []) {
  stopVerbRotation();
  statusController.verbs = words;
  statusController.verbIndex = 0;
  if (!words.length) return;
  setStatusVerb(words[0]);
  if (words.length === 1) return;
  statusController.verbHandle = setInterval(() => {
    statusController.verbIndex = (statusController.verbIndex + 1) % words.length;
    setStatusVerb(words[statusController.verbIndex]);
  }, 2300);
}

function stopVerbRotation() {
  if (statusController.verbHandle) {
    clearInterval(statusController.verbHandle);
  }
  statusController.verbHandle = null;
}

function updateTimerDisplay(value) {
  if (statusTimerEl) {
    statusTimerEl.textContent = `${String(value).padStart(2, '0')}s`;
  }
}

function startElapsedTimer() {
  if (statusController.timerHandle) {
    clearInterval(statusController.timerHandle);
  }
  statusController.timerStartedAt = Date.now();
  updateTimerDisplay(0);
  statusController.timerHandle = setInterval(() => {
    const elapsed = Math.floor((Date.now() - statusController.timerStartedAt) / 1000);
    updateTimerDisplay(elapsed);
  }, 1000);
}

function stopElapsedTimer() {
  if (statusController.timerHandle) {
    clearInterval(statusController.timerHandle);
  }
  statusController.timerHandle = null;
  statusController.timerStartedAt = null;
  updateTimerDisplay(0);
}

function ensureAudioContext() {
  if (typeof window === 'undefined') return null;
  if (!audioController.enabled) return null;
  if (audioController.ctx) return audioController.ctx;
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return null;
  audioController.ctx = new AudioContext();
  return audioController.ctx;
}

function startSonicProgress(totalEvents) {
  const ctx = ensureAudioContext();
  if (!ctx || totalEvents <= 0) return;

  stopSonicProgress();
  audioController.total = totalEvents;

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = 'sine';
  osc.frequency.value = 140;
  gain.gain.value = 0.02;
  osc.connect(gain).connect(ctx.destination);
  osc.start();

  audioController.oscillator = osc;
  audioController.gain = gain;
}

function updateSonicProgress(processedEvents) {
  const { oscillator, total } = audioController;
  if (!oscillator || !total) return;
  const ratio = Math.min(Math.max(processedEvents / total, 0), 1);
  const freq = 140 + ratio * 220;
  oscillator.frequency.setTargetAtTime(freq, oscillator.context.currentTime, 0.2);
  if (audioController.gain) {
    const gainValue = 0.01 + ratio * 0.03;
    audioController.gain.gain.setTargetAtTime(gainValue, oscillator.context.currentTime, 0.3);
  }
  if (processedEvents >= total) {
    stopSonicProgress();
  }
}

function stopSonicProgress() {
  if (audioController.oscillator) {
    try {
      audioController.oscillator.stop(0.05);
    } catch (_) {
      /* ignore */
    }
    audioController.oscillator.disconnect();
  }
  if (audioController.gain) {
    audioController.gain.disconnect();
  }
  audioController.oscillator = null;
  audioController.gain = null;
  audioController.total = 0;
}

function status(state) {
  const preset = STATUS_PRESETS[state] || STATUS_PRESETS.idle;
  statusController.state = state in STATUS_PRESETS ? state : 'idle';

  if (statusInfoEl) statusInfoEl.textContent = preset.info;

  if (statusIconEl) {
    statusIconEl.classList.remove('state-idle', 'state-busy', 'state-tool');
    statusIconEl.classList.add(preset.iconClass);
  }

  if (frame) {
    frame.classList.toggle('is-busy', state === 'busy');
    frame.classList.toggle('is-tool', state === 'tool');
  }

  startVerbRotation(preset.verbs);

  if (state === 'idle') {
    stopElapsedTimer();
    stopSonicProgress();
  } else {
    startElapsedTimer();
  }
}

function summarizePayload(payload) {
  if (!payload) return '';
  if (typeof payload === 'string') return payload;
  try {
    const text = JSON.stringify(payload);
    return text.length > 180 ? `${text.slice(0, 177)}…` : text;
  } catch (error) {
    return '';
  }
}

function extractTextsFromMessage(message = {}) {
  const content = message.content || [];
  const texts = [];
  content.forEach((block) => {
    if (block.text) texts.push(block.text);
    if (Array.isArray(block.content)) {
      block.content.forEach((inner) => {
        if (inner.text) texts.push(inner.text);
      });
    }
  });
  return texts;
}

function describeAssistantMessage(message = {}) {
  const names = (message.content || [])
    .map((block) => block.name)
    .filter(Boolean);
  return names.length ? names.join(', ') : '';
}

function formatId(value = '', visible = 6) {
  if (!value || value.length <= visible * 2) return value;
  return `${value.slice(0, visible)}…${value.slice(-4)}`;
}

function formatDuration(ms) {
  if (!ms && ms !== 0) return '';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.round((ms % 60000) / 1000);
  return `${minutes}m ${seconds.toString().padStart(2, '0')}s`;
}

function buildResultMeta(message = {}) {
  const meta = [];
  if (message.session_id) meta.push(`session ${formatId(message.session_id)}`);
  if (message.num_turns) meta.push(`${message.num_turns} turns`);
  if (message.duration_ms) meta.push(formatDuration(message.duration_ms));
  if (message.total_cost_usd) meta.push(`$${Number(message.total_cost_usd).toFixed(2)}`);
  return meta.join(' · ');
}

function createResultBlock(message = {}, { isFinal } = {}) {
  const block = document.createElement('div');
  block.className = `result-block${isFinal ? ' is-final' : ''}`;

  const head = document.createElement('div');
  head.className = 'result-head';
  head.textContent = isFinal ? 'AI> Gala rezultāts' : 'AI> Rezultāts';
  block.appendChild(head);

  const metaText = buildResultMeta(message);
  if (metaText) {
    const meta = document.createElement('div');
    meta.className = 'result-meta';
    meta.textContent = metaText;
    block.appendChild(meta);
  }

  const body = document.createElement('div');
  body.className = 'result-body';
  block.appendChild(body);

  return { block, body };
}

function escapeHTML(str = '') {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatInlineMarkdown(text = '') {
  let html = escapeHTML(text);
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/`(.+?)`/g, '<code>$1</code>');
  return html;
}

function renderMarkdown(text = '') {
  const lines = text.split(/\r?\n/);
  let html = '';
  let paragraph = [];
  let inList = false;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    html += `<p>${formatInlineMarkdown(paragraph.join(' '))}</p>`;
    paragraph = [];
  };

  const closeList = () => {
    if (inList) {
      html += '</ul>';
      inList = false;
    }
  };

  lines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) {
      flushParagraph();
      closeList();
      return;
    }

    const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)/);
    if (headingMatch) {
      flushParagraph();
      closeList();
      const level = headingMatch[1].length;
      html += `<h${level}>${formatInlineMarkdown(headingMatch[2])}</h${level}>`;
      return;
    }

    if (trimmed.startsWith('- ')) {
      flushParagraph();
      if (!inList) {
        html += '<ul>';
        inList = true;
      }
      html += `<li>${formatInlineMarkdown(trimmed.slice(2))}</li>`;
      return;
    }

    paragraph.push(trimmed);
  });

  flushParagraph();
  closeList();

  if (!html) {
    html = `<p>${formatInlineMarkdown(text)}</p>`;
  }

  return html;
}

function getPartialSnippet(data = {}) {
  const event = data.message?.event;
  if (!event) return '';
  if (event.delta?.text) return event.delta.text;
  if (event.content_block?.text) return event.content_block.text;
  const contentBlock = event.content_block || {};
  return contentBlock?.text || '';
}

function trackAssistantPartial(snippet) {
  const partial = groupingState.assistantPartial;
  if (!partial.node) {
    partial.node = appendLine({
      type: 'partial pending',
      text: snippet ? `Assistant (partial): ${snippet}` : 'Assistant (partial)…',
    });
    partial.count = 1;
    partial.lastText = snippet;
    return;
  }

  partial.count += 1;
  if (snippet) partial.lastText = snippet;
  partial.node.textContent = `Assistant (partial) · ${partial.count} bloki`;
}

function flushAssistantPartial() {
  const partial = groupingState.assistantPartial;
  if (!partial.node) return;
  const summary = partial.lastText
    ? `${partial.count} bloki · pēdējais: ${partial.lastText}`
    : `${partial.count} bloki nosūtīti`;
  partial.node.textContent = `Assistant (partial) — ${summary}`;
  partial.node.classList.remove('pending');
  groupingState.assistantPartial = {
    node: null,
    count: 0,
    lastText: '',
  };
}

function collapseUserMessage() {
  const message = groupingState.userMessage;
  if (message.node && !message.collapsed) {
    message.node.textContent = message.label || 'user_message';
    message.node.classList.add('collapsed');
    message.collapsed = true;
  }
}

function renderUserMessage(message = {}) {
  const texts = extractTextsFromMessage(message);
  const text = texts.length ? texts.join('\n\n') : 'User message (tukšs)';
  const label = message.content
    ?.map((block) => block.tool_use_id)
    .filter(Boolean)
    .map((id) => `user_message:${id}`)
    .join(' · ');
  const node = appendLine({
    type: 'user message-active',
    text,
  });
  groupingState.userMessage = {
    node,
    collapsed: false,
    label: label || 'user_message',
  };
}

function renderResultLine(resultData = {}, { isFinal } = {}) {
  const message = resultData.message || {};
  const text =
    message.result || summarizePayload(message) || 'Sesijas rezultāts nav pieejams.';
  const { block, body } = createResultBlock(message, { isFinal });

  appendLine({
    type: isFinal ? 'result final' : 'result',
    element: block,
  });

  const pace = isFinal ? 36 : 22;
  const step = isFinal ? 1 : 3;
  let index = 0;

  function tick() {
    if (index >= text.length) {
      output.scrollTop = output.scrollHeight;
      body.innerHTML = renderMarkdown(text);
      if (isFinal) status('idle');
      return;
    }

    index += step;
    body.textContent = text.slice(0, index);
    output.scrollTop = output.scrollHeight;
    setTimeout(tick, pace);
  }

  tick();
}

function renderEvent(event, options = {}) {
  const { event: type, data = {} } = event;
  const { isFinal = false } = options;

  if (type !== 'assistant_partial') {
    flushAssistantPartial();
  }
  if (type !== 'user_message') {
    collapseUserMessage();
  }

  if (type === 'conversation_id') {
    appendLine({ type: 'system', text: `conversation_id: ${data.id}` });
    return;
  }

  if (type === 'session_id') {
    appendLine({ type: 'system', text: `session_id: ${data.session_id}` });
    return;
  }

  if (type === 'system_init' || type === 'system_message') {
    return;
  }

  if (type === 'thinking_start') {
    status('busy');
    appendLine({ type: 'system', text: 'AI domā…' });
    return;
  }

  if (type === 'thinking_stop') {
    status('busy');
    appendLine({ type: 'system', text: 'AI pabeidza domāšanas posmu.' });
    return;
  }

  if (type === 'user_message') {
    renderUserMessage(data.message);
    return;
  }

  if (type === 'assistant_message') {
    const summary = describeAssistantMessage(data.message);
    appendLine({
      type: 'assistant',
      text: summary || 'Assistant message (bez nosaukuma)',
    });
    return;
  }

  if (type === 'assistant_partial') {
    const snippet = getPartialSnippet(data);
    trackAssistantPartial(snippet);
    return;
  }

  if (type === 'content_delta' && data.text) {
    appendLine({ type: 'assistant typewriter', text: data.text });
    return;
  }

  if (type === 'content_stop') {
    appendLine({ type: 'system', text: 'Assistant content stream pabeigta.' });
    return;
  }

  if (type === 'tool_use_start') {
    status('tool');
    appendLine({
      type: 'tool',
      text: `Tool start → ${data.tool_name || 'nezināms rīks'}`,
    });
    return;
  }

  if (type === 'tool_use_stop') {
    status('busy');
    appendLine({
      type: 'tool',
      text: `Tool finished → ${summarizePayload(data.tool_call)}`,
    });
    return;
  }

  if (type === 'tool_result') {
    appendLine({
      type: data.is_error ? 'warning' : 'tool',
      text: `Tool result: ${summarizePayload(data)}`,
    });
    return;
  }

  if (type === 'result') {
    renderResultLine(data, { isFinal });
    return;
  }

  if (type === 'message_stop' || type === 'message_start') {
    appendLine({ type: 'meta', text: `[${type}]` });
    if (type === 'message_stop') status('idle');
    return;
  }

  if (type === 'error') {
    appendLine({
      type: 'warning',
      text: `Kļūda straumē: ${summarizePayload(data)}`,
    });
    status('idle');
    return;
  }

  appendLine({
    type: 'system',
    text: `${type}: ${summarizePayload(data)}`,
  });
}

function streamEvents() {
  if (!logSnapshot?.events?.length) {
    appendLine({ type: 'warning', text: 'Nav saglabātu notikumu straumju.' });
    status('idle');
    stopSonicProgress();
    return;
  }

  const events = logSnapshot.events;
  const queue = [];
  let finalResult = null;

  events.forEach((evt) => {
    if (evt.event === 'result') {
      finalResult = evt;
    } else {
      queue.push(evt);
    }
  });

  const totalEvents = queue.length + (finalResult ? 1 : 0);
  let processedEvents = 0;
  if (totalEvents > 0) {
    startSonicProgress(totalEvents);
  } else {
    stopSonicProgress();
  }

  const markProcessed = () => {
    processedEvents += 1;
    updateSonicProgress(processedEvents);
  };

  status('busy');

  function next() {
    if (!queue.length) {
      if (finalResult) {
        renderEvent(finalResult, { isFinal: true });
        markProcessed();
        finalResult = null;
        return;
      }
      appendLine({
        type: 'system typewriter',
        text: 'AI> Notikumu straume pabeigta.',
      });
      status('idle');
      stopSonicProgress();
      return;
    }

    const event = queue.shift();
    renderEvent(event);
    markProcessed();

    const fast = event.event === 'content_delta';
    setTimeout(next, fast ? 80 : 260);
  }

  next();
}

promptForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const query = promptInput.value.trim();
  if (!query) return;
  if (!logSnapshot) {
    appendLine({ type: 'warning', text: 'Dati vēl nav ielādēti. Lūdzu pagaidi mirkli.' });
    return;
  }
  appendLine({ type: 'user', text: query });
  promptInput.value = '';

  appendLine({ type: 'system', text: 'AI> Atskaņoju saglabāto notikumu straumi.' });
  setTimeout(streamEvents, 600);
});

async function bootstrap() {
  try {
    const response = await fetch('./chat-stream.log');
    logSnapshot = await response.json();
    const info =
      logSnapshot && logSnapshot.events
        ? `Ielādēti ${logSnapshot.events.length} straumes notikumi`
        : 'Straumes failā nav notikumu.';
    appendLine({ type: 'system', text: `AI> ${info}` });
    appendLine({
      type: 'system',
      text: 'AI> Ievadi komandu, lai atskaņotu saglabāto straumi.',
    });
  } catch (error) {
    appendLine({ type: 'warning', text: 'Neizdevās nolasīt chat-stream.log' });
    console.error(error);
  }
}

bootstrap();
