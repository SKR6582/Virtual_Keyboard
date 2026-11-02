let socket = null;
let keys = [];
const hudGrid = document.getElementById("hud-grid");
const overlayDot = document.getElementById("overlay-dot");
const overlayStatusText = document.getElementById("overlay-status-text");

const keyElements = new Map();
let activeTimers = new Map();

function connectWebSocket() {
  socket = new WebSocket("ws://127.0.0.1:8765");

  socket.onopen = () => {
    overlayDot.style.backgroundColor = "#12b76a";
    overlayStatusText.textContent = "Active";
  };

  socket.onclose = () => {
    overlayDot.style.backgroundColor = "#f04438";
    overlayStatusText.textContent = "Offline";
    setTimeout(connectWebSocket, 1500);
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "init") {
        keys = data.keys || [];
        renderHudKeys();
      } else if (data.type === "tick") {
        updateHud(data);
      }
    } catch (e) {
      console.error("Overlay message error:", e);
    }
  };
}

function renderHudKeys() {
  hudGrid.innerHTML = "";
  keyElements.clear();

  keys.forEach((k) => {
    const el = document.createElement("div");
    el.className = "hud-key" + (k.label === "SPACE" ? " space" : "");
    el.textContent = k.label;
    hudGrid.appendChild(el);
    keyElements.set(k.label, el);
  });
}

function updateHud(data) {
  const hoverKey = data.current_key;
  const strikeKey = data.strike ? data.strike_key : null;

  // Update hover state
  keyElements.forEach((el, label) => {
    if (label === hoverKey) {
      el.classList.add("hover");
    } else {
      el.classList.remove("hover");
    }
  });

  // Update strike trigger
  if (strikeKey && keyElements.has(strikeKey)) {
    const el = keyElements.get(strikeKey);
    el.classList.add("active");

    if (activeTimers.has(strikeKey)) {
      clearTimeout(activeTimers.get(strikeKey));
    }

    const t = setTimeout(() => {
      el.classList.remove("active");
      activeTimers.delete(strikeKey);
    }, 160);

    activeTimers.set(strikeKey, t);
  }
}

connectWebSocket();

