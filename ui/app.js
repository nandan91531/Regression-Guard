document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('config-form');
  const btnRun = document.getElementById('btn-run');
  const terminalOutput = document.getElementById('terminal-output');
  const codeOutput = document.getElementById('code-output');
  const reportOutput = document.getElementById('report-output');
  const btnCopy = document.getElementById('btn-copy');
  const statusDot = document.getElementById('status-dot');
  const statusText = document.getElementById('status-text');
  const modelSelect = document.getElementById('model');
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  let activeEventSource = null;

  // Tab Switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      const targetTab = document.getElementById(btn.dataset.tab);
      if (targetTab) targetTab.classList.add('active');
    });
  });

  // Copy Code Handler
  btnCopy.addEventListener('click', () => {
    const text = codeOutput.textContent;
    if (text) {
      navigator.clipboard.writeText(text);
      btnCopy.textContent = '✅ Copied!';
      setTimeout(() => btnCopy.textContent = '📋 Copy Code', 2000);
    }
  });

  // Check Ollama Status & Fetch Models
  async function fetchModels() {
    try {
      const res = await fetch('/api/models');
      if (res.ok) {
        const data = await res.json();
        if (data.models && data.models.length > 0) {
          modelSelect.innerHTML = '';
          data.models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.name || m;
            opt.textContent = m.name || m;
            modelSelect.appendChild(opt);
          });
          statusDot.classList.remove('offline');
          statusText.textContent = `Ollama Online (${data.models.length} Models)`;
          return;
        }
      }
      throw new Error('Ollama offline');
    } catch (e) {
      statusDot.classList.add('offline');
      statusText.textContent = 'Ollama Server Offline';
    }
  }

  fetchModels();

  // Reset Stepper Progress
  function resetStepper() {
    for (let i = 1; i <= 5; i++) {
      const step = document.getElementById(`step-${i}`);
      if (step) {
        step.classList.remove('active', 'completed');
      }
    }
  }

  function setStep(stepNum, status = 'active') {
    for (let i = 1; i < stepNum; i++) {
      const prevStep = document.getElementById(`step-${i}`);
      if (prevStep) {
        prevStep.classList.remove('active');
        prevStep.classList.add('completed');
      }
    }
    const currentStep = document.getElementById(`step-${stepNum}`);
    if (currentStep) {
      currentStep.classList.remove('completed');
      currentStep.classList.add(status);
    }
  }

  // Form Submit Execution Handler
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    btnRun.disabled = true;
    btnRun.innerHTML = '<span>⏳ Running...</span>';
    terminalOutput.innerHTML = '';
    codeOutput.textContent = '# Waiting for valid generated test...';
    reportOutput.innerHTML = '<p style="color: var(--text-muted)">Generating report...</p>';
    resetStepper();

    const payload = {
      repo: document.getElementById('repo').value,
      buggy: document.getElementById('buggy').value,
      fixed: document.getElementById('fixed').value,
      test_file: document.getElementById('test-file').value,
      model: modelSelect.value,
      timeout: parseInt(document.getElementById('timeout').value) || 180,
      max_attempts: parseInt(document.getElementById('max-attempts').value) || 3
    };

    if (activeEventSource) {
      activeEventSource.close();
    }

    try {
      const startRes = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!startRes.ok) {
        throw new Error(`Failed to start execution: ${startRes.statusText}`);
      }

      // Connect SSE stream
      activeEventSource = new EventSource('/api/stream');

      activeEventSource.onmessage = (event) => {
        const line = event.data;
        if (!line) return;

        // Parse Step Markers
        if (line.includes('STEP_1')) setStep(1);
        else if (line.includes('STEP_2')) setStep(2);
        else if (line.includes('STEP_3')) setStep(3);
        else if (line.includes('STEP_4')) setStep(4);
        else if (line.includes('STEP_5')) setStep(5);
        else if (line.includes('STEP_COMPLETE')) {
          setStep(5, 'completed');
          fetchReport();
        }

        // Extract Valid Test Code Snippet
        if (line.includes('FINAL VALID TEST')) {
          const codeLines = line.split('\n').filter(l => !l.includes('FINAL VALID TEST') && !l.includes('---'));
          if (codeLines.length > 0) {
            codeOutput.textContent = codeLines.join('\n').trim();
          }
        }

        // Print Line to Terminal Window
        const lineEl = document.createElement('div');
        lineEl.className = 'terminal-line';
        if (line.includes('✅')) lineEl.classList.add('success');
        else if (line.includes('❌') || line.includes('Error')) lineEl.classList.add('error');
        else if (line.includes('🚀') || line.includes('===') || line.includes('STEP_')) lineEl.classList.add('highlight');
        else if (line.includes('⚠️')) lineEl.classList.add('warn');

        lineEl.textContent = line;
        terminalOutput.appendChild(lineEl);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
      };

      activeEventSource.onerror = (err) => {
        activeEventSource.close();
        btnRun.disabled = false;
        btnRun.innerHTML = '<span>⚡ Run Regression Guard</span>';
      };

    } catch (err) {
      const lineEl = document.createElement('div');
      lineEl.className = 'terminal-line error';
      lineEl.textContent = `Execution Error: ${err.message}`;
      terminalOutput.appendChild(lineEl);
      btnRun.disabled = false;
      btnRun.innerHTML = '<span>⚡ Run Regression Guard</span>';
    }
  });

  // Fetch Report Output
  async function fetchReport() {
    try {
      const res = await fetch('/api/report');
      if (res.ok) {
        const text = await res.text();
        reportOutput.innerHTML = parseSimpleMarkdown(text);
      }
    } catch (e) {
      reportOutput.innerHTML = '<p class="error">Could not load report.</p>';
    }
  }

  // Simple Markdown Parser for Report Rendering
  function parseSimpleMarkdown(md) {
    let html = md
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/```python([\s\S]*?)```/gim, '<pre><code class="python">$1</code></pre>')
      .replace(/```diff([\s\S]*?)```/gim, '<pre><code class="diff">$1</code></pre>')
      .replace(/\n/g, '<br>');
    return html;
  }
});
