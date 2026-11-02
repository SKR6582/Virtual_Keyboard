let socket = null;
let keys = [];
let planeSize = [1000, 600];
let currentCursor = null;
let currentHoverKey = null;
let isRecording = false;
let targetKey = "UP";
let isOsInputEnabled = true;

const wsDot = document.getElementById("ws-dot");
const wsStatusText = document.getElementById("ws-status-text");
const camCountText = document.getElementById("cam-count-text");
const calibrationText = document.getElementById("calibration-text");
const videoStream = document.getElementById("video-stream");
const hoverKeyText = document.getElementById("hover-key-text");
const canvas = document.getElementById("keyboard-canvas");
const ctx = canvas.getContext("2d");

const btnToggleOs = document.getElementById("btn-toggle-os");
const btnCalibrate = document.getElementById("btn-calibrate");
const btnToggleOverlay = document.getElementById("btn-toggle-overlay");
const selectTargetKey = document.getElementById("select-target-key");
const btnRecord = document.getElementById("btn-record");
const btnClearData = document.getElementById("btn-clear-data");
const btnTrain = document.getElementById("btn-train");
const datasetTbody = document.getElementById("dataset-tbody");
const strikeLogBox = document.getElementById("strike-log-box");

let activeStrikeKey = null;
let strikeTimer = null;

function connectWebSocket() {
  socket = new WebSocket("ws://127.0.0.1:8765");

  socket.onopen = () => {
    wsDot.classList.add("active");
    wsStatusText.textContent = "Backend Connected";
  };

  socket.onclose = () => {
    wsDot.classList.remove("active");
    wsStatusText.textContent = "Disconnected (Retrying...)";
    setTimeout(connectWebSocket, 1500);
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleMessage(data);
    } catch (e) {
      console.error("Message parsing error:", e);
    }
  };
}

function handleMessage(data) {
  if (data.type === "init") {
    keys = data.keys || [];
    planeSize = data.plane_size || [1000, 600];
    canvas.width = planeSize[0];
    canvas.height = planeSize[1];
    isOsInputEnabled = data.os_input_enabled;
    updateKeySelectOptions();
    updateDatasetStats(data.dataset_stats || {});
    renderCanvas();
    return;
  }

  if (data.type === "tick") {
    camCountText.textContent = data.active_cameras || "0";
    calibrationText.textContent = data.calibrated ? "Calibrated (ArUco)" : "Searching ArUco...";
    calibrationText.style.color = data.calibrated ? "#12b76a" : "#f04438";

    if (data.preview_frame) {
      videoStream.src = "data:image/jpeg;base64," + data.preview_frame;
    }

    currentCursor = data.cursor;
    currentHoverKey = data.current_key;
    hoverKeyText.textContent = currentHoverKey || "NONE";

    if (data.strike && data.strike_key) {
      triggerStrikeVisual(data.strike_key);
      addStrikeLog(data.strike_key);
    }

    if (data.dataset_stats) {
      updateDatasetStats(data.dataset_stats);
    }

    renderCanvas();
    return;
  }

  if (data.type === "train_result") {
    const res = data.result;
    alert(`Model Training Complete!\nSamples: ${res.sample_count}\nContact Accuracy: ${res.contact_accuracy}%\nKey Accuracy: ${res.key_accuracy}%`);
    return;
  }

  if (data.type === "os_input_status") {
    isOsInputEnabled = data.enabled;
    btnToggleOs.textContent = isOsInputEnabled ? "Enabled" : "Disabled";
    btnToggleOs.className = isOsInputEnabled ? "btn btn-primary" : "btn btn-secondary";
    return;
  }
}

function updateKeySelectOptions() {
  selectTargetKey.innerHTML = "";
  keys.forEach((k) => {
    const opt = document.createElement("option");
    opt.value = k.label;
    opt.textContent = k.label;
    selectTargetKey.appendChild(opt);
  });
  if (keys.length > 0) {
    targetKey = keys[0].label;
  }
}

function updateDatasetStats(stats) {
  datasetTbody.innerHTML = "";
  const entries = Object.entries(stats);
  if (entries.length === 0) {
    datasetTbody.innerHTML = `<tr><td colspan="2" style="color: #667085;">No training samples yet</td></tr>`;
    return;
  }
  entries.forEach(([key, count]) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td><strong>${key}</strong></td><td>${count}</td>`;
    datasetTbody.appendChild(tr);
  });
}

function triggerStrikeVisual(keyLabel) {
  activeStrikeKey = keyLabel;
  if (strikeTimer) clearTimeout(strikeTimer);
  strikeTimer = setTimeout(() => {
    activeStrikeKey = null;
    renderCanvas();
  }, 180);
}

function addStrikeLog(keyLabel) {
  const timeStr = new Date().toLocaleTimeString();
  const entry = document.createElement("div");
  entry.className = "log-entry active";
  entry.textContent = `[${timeStr}] Key Pressed: ${keyLabel}`;
  strikeLogBox.prepend(entry);

  if (strikeLogBox.children.length > 30) {
    strikeLogBox.removeChild(strikeLogBox.lastChild);
  }
}

function renderCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Background grid
  ctx.strokeStyle = "#1e2025";
  ctx.lineWidth = 1;
  const step = 50;
  for (let x = 0; x < canvas.width; x += step) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y < canvas.height; y += step) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
    ctx.stroke();
  }

  // Draw keys
  keys.forEach((k) => {
    const [x1, y1, x2, y2] = k.bbox;
    const w = x2 - x1;
    const h = y2 - y1;
    const isHovered = currentHoverKey === k.label;
    const isStruck = activeStrikeKey === k.label;

    if (isStruck) {
      ctx.fillStyle = "#2970ff";
      ctx.strokeStyle = "#84caff";
      ctx.lineWidth = 3;
    } else if (isHovered) {
      ctx.fillStyle = "#2e3138";
      ctx.strokeStyle = "#53b1fd";
      ctx.lineWidth = 2;
    } else {
      ctx.fillStyle = "#1e2025";
      ctx.strokeStyle = "#383a42";
      ctx.lineWidth = 1.5;
    }

    ctx.fillRect(x1, y1, w, h);
    ctx.strokeRect(x1, y1, w, h);

    // Key label
    ctx.fillStyle = isStruck ? "#ffffff" : isHovered ? "#53b1fd" : "#d0d5dd";
    ctx.font = "bold 16px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(k.label, x1 + w / 2, y1 + h / 2);
  });

  // Draw tracked fingertip cursor
  if (currentCursor) {
    const cx = currentCursor.x;
    const cy = currentCursor.y;

    ctx.beginPath();
    ctx.arc(cx, cy, 10, 0, Math.PI * 2);
    ctx.fillStyle = activeStrikeKey ? "#f04438" : "rgba(83, 177, 253, 0.85)";
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();
  }
}

// Button Events
btnToggleOs.addEventListener("click", () => {
  const next = !isOsInputEnabled;
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action: "toggle_os_input", enabled: next }));
  }
});

btnCalibrate.addEventListener("click", () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action: "calibrate_aruco" }));
  }
});

btnToggleOverlay.addEventListener("click", () => {
  if (window.electronAPI) {
    window.electronAPI.toggleOverlay();
  }
});

selectTargetKey.addEventListener("change", (e) => {
  targetKey = e.target.value;
});

btnRecord.addEventListener("click", () => {
  isRecording = !isRecording;
  if (isRecording) {
    btnRecord.textContent = "Stop Recording";
    btnRecord.className = "btn btn-danger";
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: "start_collection", key_label: targetKey }));
    }
  } else {
    btnRecord.textContent = "Record Samples";
    btnRecord.className = "btn btn-primary";
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: "stop_collection" }));
    }
  }
});

btnClearData.addEventListener("click", () => {
  if (confirm("Are you sure you want to clear all collected samples?")) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: "clear_dataset" }));
    }
  }
});

btnTrain.addEventListener("click", () => {
  btnTrain.disabled = true;
  btnTrain.textContent = "Training...";
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ action: "train_model" }));
  }
  setTimeout(() => {
    btnTrain.disabled = false;
    btnTrain.textContent = "Train Model (.pkl)";
  }, 2000);
});

connectWebSocket();

