let socket = null;
let keys = [];
let planeSize = [1000, 600];
let currentHoverKey = null;
let isRecording = false;
let targetKey = "UP";
let isOsInputEnabled = true;
let primaryCameraIndex = 0;

const wsDot = document.getElementById("ws-dot");
const wsStatusText = document.getElementById("ws-status-text");
const camCountText = document.getElementById("cam-count-text");
const calibrationText = document.getElementById("calibration-text");
const videoStream = document.getElementById("video-stream");
const lastStrikeKeyText = document.getElementById("last-strike-key-text");
const canvas = document.getElementById("keyboard-canvas");
const ctx = canvas.getContext("2d");

const selectCamera = document.getElementById("select-camera");
const btnRefreshCameras = document.getElementById("btn-refresh-cameras");

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
    primaryCameraIndex = data.primary_camera !== undefined ? data.primary_camera : 0;
    
    updateCameraOptions(data.available_cameras || [0], primaryCameraIndex, data.is_simulation);
    updateKeySelectOptions();
    updateDatasetStats(data.dataset_stats || {});
    renderCanvas();
    return;
  }

  if (data.type === "available_cameras") {
    updateCameraOptions(data.available_cameras || [0], data.primary_camera !== undefined ? data.primary_camera : primaryCameraIndex);
    return;
  }

  if (data.type === "camera_switched") {
    primaryCameraIndex = data.primary_camera;
    selectCamera.value = String(data.primary_camera);
    return;
  }

  if (data.type === "tick") {
    camCountText.textContent = data.active_cameras || "0";
    calibrationText.textContent = data.calibrated ? "Calibrated (ArUco)" : "Searching ArUco...";
    calibrationText.style.color = data.calibrated ? "#12b76a" : "#f04438";

    if (data.preview_frame) {
      videoStream.src = "data:image/jpeg;base64," + data.preview_frame;
    }

    currentHoverKey = data.current_key;

    if (data.strike && data.strike_key) {
      triggerStrikeVisual(data.strike_key);
      addStrikeLog(data.strike_key);
      if (lastStrikeKeyText) {
        lastStrikeKeyText.textContent = data.strike_key;
      }
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

function updateCameraOptions(availableIndices, currentIdx, isSimulation = false) {
  if (!selectCamera) return;
  selectCamera.innerHTML = "";

  const unique = Array.from(new Set(availableIndices)).sort((a, b) => a - b);
  unique.forEach((idx) => {
    const opt = document.createElement("option");
    opt.value = String(idx);
    opt.textContent = `Camera ${idx} (Physical)`;
    if (idx === currentIdx && !isSimulation) {
      opt.selected = true;
    }
    selectCamera.appendChild(opt);
  });

  const simOpt = document.createElement("option");
  simOpt.value = "-1";
  simOpt.textContent = "Simulated Keyboard (Test)";
  if (isSimulation) {
    simOpt.selected = true;
  }
  selectCamera.appendChild(simOpt);
}

function updateKeySelectOptions() {
  if (!selectTargetKey) return;
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
  if (!datasetTbody) return;
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
  }, 220);
}

function addStrikeLog(keyLabel) {
  if (!strikeLogBox) return;
  const timeStr = new Date().toLocaleTimeString();
  const entry = document.createElement("div");
  entry.className = "log-entry active";
  entry.textContent = `[${timeStr}] STRIKE: ${keyLabel}`;
  strikeLogBox.prepend(entry);

  if (strikeLogBox.children.length > 30) {
    strikeLogBox.removeChild(strikeLogBox.lastChild);
  }
}

function renderCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Background subtle grid
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

  // Draw Physical Keyboard Layout & Strike State
  keys.forEach((k) => {
    const [x1, y1, x2, y2] = k.bbox;
    const w = x2 - x1;
    const h = y2 - y1;
    const isStruck = activeStrikeKey === k.label;

    if (isStruck) {
      // Physical key hit flash
      ctx.fillStyle = "rgba(18, 183, 106, 0.9)";
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 4;
      ctx.shadowColor = "#12b76a";
      ctx.shadowBlur = 16;
    } else {
      ctx.fillStyle = "#1e2025";
      ctx.strokeStyle = "#383a42";
      ctx.lineWidth = 1.5;
      ctx.shadowBlur = 0;
    }

    ctx.fillRect(x1, y1, w, h);
    ctx.strokeRect(x1, y1, w, h);
    ctx.shadowBlur = 0;

    // Key label
    ctx.fillStyle = isStruck ? "#ffffff" : "#d0d5dd";
    ctx.font = isStruck ? "bold 20px sans-serif" : "bold 16px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(k.label, x1 + w / 2, y1 + h / 2);
  });
}

// Camera controls
if (selectCamera) {
  selectCamera.addEventListener("change", (e) => {
    const camIdx = parseInt(e.target.value, 10);
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: "switch_camera", camera_index: camIdx }));
    }
  });
}

if (btnRefreshCameras) {
  btnRefreshCameras.addEventListener("click", () => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: "refresh_cameras" }));
    }
  });
}

// System controls
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
