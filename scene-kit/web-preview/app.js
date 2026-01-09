let data = null;
let currentNode = null;
let introShown = false;

const fileInput = document.getElementById('fileInput');
const metaEl = document.getElementById('meta');
const narrationEl = document.getElementById('narration');
const choicesEl = document.getElementById('choices');
const endingEl = document.getElementById('ending');

fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  const text = await file.text();
  try {
    data = JSON.parse(text);
  } catch (err) {
    alert('Invalid JSON');
    return;
  }
  start();
});

function start() {
  introShown = false;
  endingEl.textContent = '';
  renderMeta();
  // Start at N1 if present, else first node
  const nodeIds = (data.nodes || []).map(n => n.nodeId);
  const startId = nodeIds.includes('N1') ? 'N1' : (nodeIds[0] || null);
  currentNode = startId;
  render();
}

function renderMeta() {
  metaEl.innerHTML = '';
  const b1 = badge(data.sceneId);
  const b2 = badge(data.variantId || 'variant');
  const b3 = badge((data.uiHints || []).join(' · '));
  metaEl.appendChild(b1); metaEl.appendChild(b2); metaEl.appendChild(b3);
}

function badge(txt) {
  const span = document.createElement('span'); span.className = 'badge'; span.textContent = txt;
  return span;
}

function render() {
  if (!data) return;
  if (!introShown && data.intro) {
    narrationEl.textContent = data.intro.narration || '';
    choicesEl.innerHTML = '<div class="choice">Continue</div>';
    choicesEl.firstChild.onclick = () => { introShown = true; render(); };
    return;
  }
  const node = (data.nodes || []).find(n => n.nodeId === currentNode);
  if (!node) {
    narrationEl.textContent = '';
    choicesEl.innerHTML = '';
    return;
  }
  narrationEl.textContent = node.narration || '';
  choicesEl.innerHTML = '';
  (node.choices || []).forEach((c, idx) => {
    const btn = document.createElement('div');
    btn.className = 'choice';
    btn.textContent = `${idx+1}. ${c.text}`;
    btn.onclick = () => choose(c.to);
    choicesEl.appendChild(btn);
  });
}

function choose(target) {
  // If target is an endingId, show ending
  const ending = (data.endings || []).find(e => e.endingId === target);
  if (ending) {
    narrationEl.textContent = '';
    choicesEl.innerHTML = '';
    endingEl.innerHTML = `<h3>${ending.title} (${ending.type})</h3><p>${ending.narration}</p>`;
    return;
  }
  currentNode = target;
  render();
}

document.addEventListener('keydown', (e) => {
  if (e.key.toLowerCase() === 'r') start();
  const idx = parseInt(e.key, 10) - 1;
  if (!isNaN(idx)) {
    const buttons = document.querySelectorAll('.choice');
    if (buttons[idx]) buttons[idx].click();
  }
});
