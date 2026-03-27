// SanStudio Sample Project — script.js

// ── Counter (localStorage) ────────────────────────────────────────────────
let count = parseInt(localStorage.getItem('san_counter') || '0');

function renderCounter() {
  const el = document.getElementById('counterDisplay');
  el.textContent = count;
  el.classList.add('bump');
  setTimeout(() => el.classList.remove('bump'), 120);
}

function updateCounter(delta) {
  count += delta;
  localStorage.setItem('san_counter', count);
  renderCounter();
}

function resetCounter() {
  count = 0;
  localStorage.setItem('san_counter', 0);
  renderCounter();
}

renderCounter();

// ── localStorage test ─────────────────────────────────────────────────────
function testStorage() {
  const key = 'san_test_' + Date.now();
  try {
    localStorage.setItem(key, '✔ works!');
    const val = localStorage.getItem(key);
    localStorage.removeItem(key);
    document.getElementById('storeResult').textContent = val;
    document.getElementById('storeResult').style.color = '#22C55E';
  } catch (e) {
    document.getElementById('storeResult').textContent = '✘ Error';
    document.getElementById('storeResult').style.color = '#EF4444';
  }
}

// ── Fetch quote (online API demo) ─────────────────────────────────────────
async function fetchQuote() {
  const el = document.getElementById('quoteResult');
  el.textContent = 'Fetching…';
  try {
    const res = await fetch('https://api.quotable.io/random?maxLength=80');
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    el.textContent = `"${data.content}" — ${data.author}`;
    el.style.color = '#4F8EF7';
  } catch {
    el.textContent = '(Offline or API unavailable)';
    el.style.color = '#EF4444';
  }
}
