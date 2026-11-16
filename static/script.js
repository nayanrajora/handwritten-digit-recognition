/**
 * Handwritten Digit Recognition System - Frontend Controller
 * B.Tech Capstone Project
 * Handles Canvas drawing, touch interactions, REST API calls, and real-time visualization.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const canvas = document.getElementById('digit-canvas');
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const clearBtn = document.getElementById('clear-btn');
  const predictBtn = document.getElementById('predict-btn');
  const brushSlider = document.getElementById('brush-size');
  const brushVal = document.getElementById('brush-val');
  const canvasHint = document.getElementById('canvas-hint');
  const errorAlert = document.getElementById('error-alert');
  const errorMessage = document.getElementById('error-message');
  const statusTag = document.getElementById('status-tag');
  const emptyState = document.getElementById('empty-state');
  const resultContent = document.getElementById('result-content');
  const predictedDigitEl = document.getElementById('predicted-digit');
  const predictionConfidenceEl = document.getElementById('prediction-confidence');
  const inferenceTimeEl = document.getElementById('inference-time');
  const processedImgPreview = document.getElementById('processed-img-preview');
  const probBarsContainer = document.getElementById('prob-bars');
  const sampleBtns = document.querySelectorAll('.sample-btn');

  // Drawing state
  let isDrawing = false;
  let hasDrawn = false;
  let strokeWidth = parseInt(brushSlider.value, 10) || 20;

  // Initialize Canvas to White Background
  function initCanvas() {
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = strokeWidth;
  }

  initCanvas();

  // Brush Slider
  brushSlider.addEventListener('input', (e) => {
    strokeWidth = parseInt(e.target.value, 10);
    brushVal.textContent = `${strokeWidth}px`;
    ctx.lineWidth = strokeWidth;
  });

  // Get pointer coordinates relative to canvas
  function getCanvasPos(evt) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    let clientX, clientY;
    if (evt.touches && evt.touches.length > 0) {
      clientX = evt.touches[0].clientX;
      clientY = evt.touches[0].clientY;
    } else {
      clientX = evt.clientX;
      clientY = evt.clientY;
    }

    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY
    };
  }

  // Mouse / Touch Handlers
  function startDrawing(e) {
    e.preventDefault();
    isDrawing = true;
    hasDrawn = true;
    canvasHint.style.opacity = '0';
    hideError();

    const pos = getCanvasPos(e);
    ctx.beginPath();
    ctx.moveTo(pos.x, pos.y);
    // Draw a single dot if clicked without moving
    ctx.lineTo(pos.x + 0.1, pos.y + 0.1);
    ctx.stroke();
  }

  function draw(e) {
    if (!isDrawing) return;
    e.preventDefault();
    const pos = getCanvasPos(e);
    ctx.lineTo(pos.x, pos.y);
    ctx.stroke();
  }

  function stopDrawing(e) {
    if (isDrawing) {
      ctx.closePath();
      isDrawing = false;
    }
  }

  // Mouse Listeners
  canvas.addEventListener('mousedown', startDrawing);
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('mouseup', stopDrawing);
  canvas.addEventListener('mouseleave', stopDrawing);

  // Touch Listeners (Mobile & Tablet Support)
  canvas.addEventListener('touchstart', startDrawing, { passive: false });
  canvas.addEventListener('touchmove', draw, { passive: false });
  canvas.addEventListener('touchend', stopDrawing);
  canvas.addEventListener('touchcancel', stopDrawing);

  // Clear Canvas
  function resetCanvas() {
    initCanvas();
    hasDrawn = false;
    canvasHint.style.opacity = '1';
    hideError();
    emptyState.style.display = 'block';
    resultContent.style.display = 'none';
    statusTag.className = 'status-indicator ready';
    statusTag.innerHTML = '<span class="dot"></span> Ready for Input';
  }

  clearBtn.addEventListener('click', resetCanvas);

  // Check if canvas has any non-white pixels
  function isCanvasBlank() {
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imgData.data;
    // Check if any pixel differs significantly from white (#ffffff)
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      // Black stroke has r, g, b < 200
      if (r < 200 || g < 200 || b < 200) {
        return false;
      }
    }
    return true;
  }

  function showError(msg) {
    errorMessage.textContent = msg;
    errorAlert.style.display = 'flex';
  }

  function hideError() {
    errorAlert.style.display = 'none';
  }

  // Predict Digit Action
  predictBtn.addEventListener('click', async () => {
    if (isCanvasBlank()) {
      showError('Please draw a digit (0–9) on the canvas before predicting!');
      return;
    }

    hideError();
    statusTag.className = 'status-indicator processing';
    statusTag.innerHTML = '<span class="dot"></span> Running CNN Inference...';
    predictBtn.disabled = true;

    const startTime = performance.now();
    const imageData = canvas.toDataURL('image/png');

    try {
      const response = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData })
      });

      const result = await response.json();
      const endTime = performance.now();
      const clientLatency = Math.round(endTime - startTime);

      if (!response.ok || !result.success) {
        showError(result.error || 'Server error occurred during prediction.');
        statusTag.className = 'status-indicator ready';
        statusTag.innerHTML = '<span class="dot"></span> Error';
        return;
      }

      displayPredictionResult(result, clientLatency);
    } catch (err) {
      console.error('Prediction request error:', err);
      showError('Failed to communicate with prediction backend. Is the Flask server running?');
      statusTag.className = 'status-indicator ready';
      statusTag.innerHTML = '<span class="dot"></span> Server Unreachable';
    } finally {
      predictBtn.disabled = false;
    }
  });

  // Display Prediction Results
  function displayPredictionResult(data, latencyMs) {
    emptyState.style.display = 'none';
    resultContent.style.display = 'block';

    predictedDigitEl.textContent = data.predicted_digit;
    predictionConfidenceEl.textContent = `${(data.confidence * 100).toFixed(2)}%`;
    inferenceTimeEl.textContent = `${data.inference_time_ms || latencyMs} ms`;

    // Processed 28x28 preview
    if (data.preprocessed_preview) {
      processedImgPreview.src = data.preprocessed_preview;
    }

    // Render probability bars for digits 0-9
    probBarsContainer.innerHTML = '';
    const probs = data.probabilities;

    for (let digit = 0; digit < 10; digit++) {
      const prob = probs[digit] || 0;
      const pct = (prob * 100).toFixed(2);
      const isTop = digit === data.predicted_digit;

      const row = document.createElement('div');
      row.className = `prob-row ${isTop ? 'active' : ''}`;
      row.innerHTML = `
        <span class="prob-digit">${digit}</span>
        <div class="prob-bar-wrapper">
          <div class="prob-fill" style="width: 0%;"></div>
        </div>
        <span class="prob-percent">${pct}%</span>
      `;
      probBarsContainer.appendChild(row);

      // Trigger width transition smoothly
      setTimeout(() => {
        const fill = row.querySelector('.prob-fill');
        if (fill) fill.style.width = `${pct}%`;
      }, 50);
    }

    statusTag.className = 'status-indicator ready';
    statusTag.innerHTML = '<span class="dot"></span> Prediction Complete';
  }

  // Preset handwritten samples drawing helper
  const digitDrawings = {
    0: (c) => {
      c.beginPath();
      c.ellipse(140, 140, 50, 80, 0, 0, Math.PI * 2);
      c.stroke();
    },
    1: (c) => {
      c.beginPath();
      c.moveTo(115, 80);
      c.lineTo(145, 55);
      c.lineTo(145, 220);
      c.stroke();
    },
    2: (c) => {
      c.beginPath();
      c.moveTo(95, 95);
      c.bezierCurveTo(95, 50, 190, 50, 185, 110);
      c.bezierCurveTo(180, 145, 130, 180, 95, 215);
      c.lineTo(190, 215);
      c.stroke();
    },
    3: (c) => {
      c.beginPath();
      c.moveTo(95, 75);
      c.lineTo(180, 75);
      c.lineTo(135, 135);
      c.bezierCurveTo(175, 135, 195, 160, 190, 195);
      c.bezierCurveTo(185, 225, 135, 230, 95, 205);
      c.stroke();
    },
    4: (c) => {
      c.beginPath();
      c.moveTo(170, 60);
      c.lineTo(90, 165);
      c.lineTo(195, 165);
      c.moveTo(165, 60);
      c.lineTo(165, 220);
      c.stroke();
    },
    5: (c) => {
      c.beginPath();
      c.moveTo(180, 70);
      c.lineTo(110, 70);
      c.lineTo(105, 130);
      c.bezierCurveTo(135, 115, 190, 125, 185, 175);
      c.bezierCurveTo(180, 220, 125, 225, 95, 200);
      c.stroke();
    },
    6: (c) => {
      c.beginPath();
      c.moveTo(170, 75);
      c.bezierCurveTo(120, 90, 95, 140, 95, 175);
      c.bezierCurveTo(95, 220, 175, 225, 175, 175);
      c.bezierCurveTo(175, 135, 95, 145, 95, 175);
      c.stroke();
    },
    7: (c) => {
      c.beginPath();
      c.moveTo(90, 70);
      c.lineTo(190, 70);
      c.lineTo(125, 220);
      c.stroke();
    },
    8: (c) => {
      c.beginPath();
      c.ellipse(140, 100, 38, 38, 0, 0, Math.PI * 2);
      c.stroke();
      c.beginPath();
      c.ellipse(140, 170, 48, 48, 0, 0, Math.PI * 2);
      c.stroke();
    },
    9: (c) => {
      c.beginPath();
      c.ellipse(140, 105, 42, 42, 0, 0, Math.PI * 2);
      c.stroke();
      c.beginPath();
      c.moveTo(180, 105);
      c.lineTo(170, 185);
      c.bezierCurveTo(165, 215, 130, 225, 100, 215);
      c.stroke();
    }
  };

  sampleBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const d = parseInt(btn.dataset.digit, 10);
      resetCanvas();
      canvasHint.style.opacity = '0';
      hasDrawn = true;
      ctx.lineWidth = strokeWidth;
      if (digitDrawings[d]) {
        digitDrawings[d](ctx);
      }
      // Auto-trigger prediction
      predictBtn.click();
    });
  });

  // Load Model Performance Metrics from Backend
  async function loadMetrics() {
    try {
      const res = await fetch('/api/metrics');
      if (!res.ok) return;
      const data = await res.json();

      // Update KPI
      if (data.test_accuracy) {
        const accPct = (data.test_accuracy * 100).toFixed(2) + '%';
        const kpiAcc = document.getElementById('kpi-accuracy');
        const heroAcc = document.getElementById('hero-acc');
        if (kpiAcc) kpiAcc.textContent = accPct;
        if (heroAcc) heroAcc.textContent = accPct;
      }
      if (data.test_loss !== undefined) {
        const kpiLoss = document.getElementById('kpi-loss');
        if (kpiLoss) kpiLoss.textContent = data.test_loss.toFixed(4);
      }
      if (data.total_parameters) {
        const kpiParams = document.getElementById('kpi-params');
        if (kpiParams) kpiParams.textContent = Number(data.total_parameters).toLocaleString();
      }
      if (data.epochs_trained) {
        const kpiEpochs = document.getElementById('kpi-epochs');
        if (kpiEpochs) kpiEpochs.textContent = data.epochs_trained;
      }

      // Populate Classification Table
      const tableBody = document.getElementById('metrics-table-body');
      if (tableBody && data.classification_report) {
        tableBody.innerHTML = '';
        const report = data.classification_report;

        for (let i = 0; i < 10; i++) {
          const digitKey = String(i);
          if (report[digitKey]) {
            const item = report[digitKey];
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td><strong>Digit ${i}</strong></td>
              <td>${(item.precision * 100).toFixed(2)}%</td>
              <td>${(item.recall * 100).toFixed(2)}%</td>
              <td>${(item['f1-score'] * 100).toFixed(2)}%</td>
              <td>${item.support.toLocaleString()}</td>
            `;
            tableBody.appendChild(tr);
          }
        }

        if (report['macro avg']) {
          const macroEl = document.getElementById('macro-f1');
          if (macroEl) macroEl.textContent = (report['macro avg']['f1-score'] * 100).toFixed(2) + '%';
        }
        if (report['weighted avg']) {
          const weightedEl = document.getElementById('weighted-f1');
          if (weightedEl) weightedEl.textContent = (report['weighted avg']['f1-score'] * 100).toFixed(2) + '%';
        }
      }

      // Refresh chart images with cache buster
      const t = Date.now();
      const chartAcc = document.getElementById('chart-accuracy');
      const chartLoss = document.getElementById('chart-loss');
      const chartConf = document.getElementById('chart-confusion');

      if (chartAcc) chartAcc.src = `/results/accuracy.png?v=${t}`;
      if (chartLoss) chartLoss.src = `/results/loss.png?v=${t}`;
      if (chartConf) chartConf.src = `/results/confusion_matrix.png?v=${t}`;

    } catch (e) {
      console.warn('Could not fetch model metrics yet:', e);
    }
  }

  // Load metrics once DOM is ready
  loadMetrics();
});

