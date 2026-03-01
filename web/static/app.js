const ws = new WebSocket(`ws://${location.host}/api/ws`);
const statusEl = document.getElementById("ws-status");
ws.onopen = () => {
  statusEl.textContent = "WS Connected";
};
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  document.getElementById("balance-pill").textContent = Number(data.balance).toFixed(2);
  document.getElementById("pnl-pill").textContent = `${(Number(data.pnl) * 100).toFixed(2)}%`;
  const logBox = document.getElementById("live-logs");
  logBox.textContent = data.logs.join("\n");
  ws.send("ack");
};
ws.onclose = () => {
  statusEl.textContent = "WS Disconnected";
};
