'use strict';
(() => {
  const samples = [
    {title:'Firmware Auto', tag:'0 / 0', cpu:3125, gpu:3703, next:'See Max mode', description:'Firmware chooses fan speeds automatically. These are the measured baseline values from our development laptop.'},
    {title:'Maximum cooling', tag:'100% / 100%', cpu:5769, gpu:5660, next:'See Custom mode', description:'An eight-second Max request raised both measured fan speeds. Automatic control was restored immediately after the test.'},
    {title:'Independent custom', tag:'60% / 70%', cpu:4615, gpu:5769, next:'Back to Auto', description:'Separate CPU and GPU requests, measured through Acer’s fan sensors. Percentages are requested settings, not RPM. Auto was restored afterward.'}
  ];
  const next = document.getElementById('next-mode');
  let index = 0;
  if (next) {
    next.hidden = false;
    next.addEventListener('click', () => {
      index = (index + 1) % samples.length;
      const sample = samples[index];
      document.getElementById('mode-title').textContent = sample.title;
      document.getElementById('mode-tag').textContent = sample.tag;
      document.getElementById('cpu-rpm').textContent = sample.cpu.toLocaleString('en-US');
      document.getElementById('gpu-rpm').textContent = sample.gpu.toLocaleString('en-US');
      document.getElementById('cpu-track').style.setProperty('--reading', `${sample.cpu / 6000 * 100}%`);
      document.getElementById('gpu-track').style.setProperty('--reading', `${sample.gpu / 6000 * 100}%`);
      document.getElementById('mode-description').textContent = sample.description;
      document.getElementById('sample-status').textContent = `${sample.title}. Recorded CPU ${sample.cpu.toLocaleString('en-US')} RPM and GPU ${sample.gpu.toLocaleString('en-US')} RPM.`;
      document.getElementById('mode-position').textContent = `0${index + 1} / 03`;
      next.replaceChildren(document.createTextNode(sample.next + ' '));
      const arrow = document.createElement('span'); arrow.setAttribute('aria-hidden', 'true'); arrow.textContent = '↗'; next.append(arrow);
    });
  }

  function selectText(node) {
    const range = document.createRange(); range.selectNodeContents(node);
    const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range);
  }
  function copyButton(buttonId, text, target, statusId) {
    const button = document.getElementById(buttonId); if (!button) return;
    const status = document.getElementById(statusId);
    const original = button.innerHTML; let timer;
    button.hidden = false;
    button.addEventListener('click', async () => {
      try {
        if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(text());
        button.textContent = 'Copied'; status.textContent = buttonId === 'copy-link' ? 'Page link copied.' : 'Installation commands copied.';
      } catch {
        if (target) { selectText(target); status.textContent = 'Commands selected. Press Ctrl+C or use your device’s Copy action.'; }
        else { status.textContent = text(); }
        button.textContent = target ? 'Text selected' : 'Link shown below';
      }
      clearTimeout(timer); timer = setTimeout(() => { button.innerHTML = original; }, 2200);
    });
  }
  const code = document.getElementById('install-code');
  copyButton('copy-install', () => code.textContent.trim(), code, 'copy-status');
  copyButton('copy-link', () => 'https://dahuum.github.io/nitro-sense-linux/', null, 'share-status');

  const themeButton = document.querySelector('.theme-toggle');
  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    themeButton?.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
    themeButton?.setAttribute('aria-pressed', String(theme === 'light'));
    document.querySelector('meta[name="theme-color"]').content = theme === 'dark' ? '#151313' : '#f6f0e9';
  }
  let saved; try { saved = localStorage.getItem('nitro-site-theme'); } catch { /* Storage may be disabled. */ }
  setTheme(saved === 'light' ? 'light' : 'dark');
  if (themeButton) {
    themeButton.hidden = false;
    themeButton.addEventListener('click', () => {
      const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      setTheme(theme); try { localStorage.setItem('nitro-site-theme', theme); } catch { /* Appearance still works without storage. */ }
    });
  }
})();
