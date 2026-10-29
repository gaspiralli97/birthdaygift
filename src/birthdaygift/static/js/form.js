/* Create-form behaviour: live preview while typing, then submit and show the
 * link. The preview is client-side only - the letter itself is written by the
 * server, so it appears with the result rather than before it.
 */
(() => {
  'use strict';

  const form = document.getElementById('create-form');
  if (!form) return;

  const themes = JSON.parse(document.getElementById('theme-data').textContent);
  const root = document.documentElement;

  const el = (id) => document.getElementById(id);
  const nameInput = el('name');
  const ageInput = el('age');
  const previewName = el('preview-name');
  const previewAge = el('preview-age');
  const previewCandles = el('preview-candles');
  const errorBox = el('form-error');
  const submit = el('submit');
  const result = el('result');

  const MAX_PREVIEW_CANDLES = 40;
  const placeholder = nameInput.placeholder;

  // --- live preview ------------------------------------------------------

  const applyTheme = (key) => {
    const theme = themes[key];
    if (!theme) return;
    for (const [property, value] of Object.entries(theme.variables)) {
      root.style.setProperty(property, value);
    }
    root.style.colorScheme = theme.color_scheme;
  };

  const renderCandles = (count) => {
    const wanted = Math.min(Math.max(count || 0, 0), MAX_PREVIEW_CANDLES);
    while (previewCandles.children.length > wanted) {
      previewCandles.lastElementChild.remove();
    }
    while (previewCandles.children.length < wanted) {
      const candle = document.createElement('div');
      candle.className = 'candle';
      candle.innerHTML = '<span class="flame"></span><span class="stick"></span>';
      previewCandles.appendChild(candle);
    }
  };

  const refresh = () => {
    previewName.textContent = nameInput.value.trim() || placeholder;
    const age = Number.parseInt(ageInput.value, 10);
    const valid = Number.isFinite(age) && age > 0 && age < 130;
    previewAge.hidden = !valid;
    previewAge.textContent = valid ? String(age) : '';
    renderCandles(valid ? age : 0);
  };

  form.addEventListener('input', (event) => {
    if (event.target.name === 'theme') applyTheme(event.target.value);
    refresh();
  });
  refresh();

  // --- submit ------------------------------------------------------------

  const showError = (message) => {
    errorBox.textContent = message;
    errorBox.hidden = false;
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    errorBox.hidden = true;

    const data = new FormData(form);
    const age = Number.parseInt(data.get('age'), 10);
    const payload = {
      name: (data.get('name') || '').trim(),
      age: Number.isFinite(age) ? age : null,
      relation: data.get('relation'),
      lang: data.get('lang'),
      theme: data.get('theme'),
      details: (data.get('details') || '').trim(),
      from_name: (data.get('from_name') || '').trim(),
    };

    if (payload.name.length < 2) {
      showError(form.dataset.errorName || 'Name is required');
      nameInput.focus();
      return;
    }

    const label = submit.textContent;
    submit.disabled = true;
    submit.textContent = submit.dataset.submitting || label;

    try {
      const response = await fetch('/api/cards', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const body = await response.json();

      if (!response.ok) {
        showError(body.message || form.dataset.errorGeneric || 'Error');
        return;
      }

      el('result-link').textContent = body.url;
      el('result-open').href = body.url;
      result.hidden = false;
      result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch {
      showError(form.dataset.errorGeneric || 'Network error');
    } finally {
      submit.disabled = false;
      submit.textContent = label;
    }
  });

  // --- result actions ----------------------------------------------------

  el('result-copy').addEventListener('click', async (event) => {
    const button = event.currentTarget;
    const url = el('result-link').textContent;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Clipboard access can be refused; selecting the text is the fallback.
      const range = document.createRange();
      range.selectNodeContents(el('result-link'));
      getSelection().removeAllRanges();
      getSelection().addRange(range);
      return;
    }
    button.textContent = button.dataset.copied;
    setTimeout(() => {
      button.textContent = button.dataset.copy;
    }, 1600);
  });

  el('result-again').addEventListener('click', () => {
    result.hidden = true;
    form.reset();
    applyTheme(form.querySelector('input[name=theme]:checked').value);
    refresh();
    nameInput.focus();
  });
})();
