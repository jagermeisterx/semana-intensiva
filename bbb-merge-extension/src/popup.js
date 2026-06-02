const deskshareDot = document.getElementById('deskshare-dot');
const webcamsDot = document.getElementById('webcams-dot');
const statusMsg = document.getElementById('status-message');
const mergeBtn = document.getElementById('merge-btn');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress-bar');

function updateUI(state) {
  deskshareDot.className = 'status-dot ' + (state.deskshareUrl ? 'found' : 'pending');
  webcamsDot.className = 'status-dot ' + (state.webcamsUrl ? 'found' : 'pending');

  const hasVideos = state.deskshareUrl || state.webcamsUrl;

  switch (state.status) {
    case 'idle':
      statusMsg.textContent = hasVideos
        ? 'Videos detectados. Haz clic en "Unir y descargar".'
        : 'Esperando datos... Abre una grabación BBB.';
      mergeBtn.disabled = !hasVideos;
      mergeBtn.className = 'merge-btn';
      mergeBtn.textContent = '🔀 Unir y descargar';
      progressContainer.style.display = 'none';
      break;

    case 'ready':
      statusMsg.textContent = 'Listo para unir.';
      mergeBtn.disabled = false;
      mergeBtn.className = 'merge-btn';
      mergeBtn.textContent = '🔀 Unir y descargar';
      progressContainer.style.display = 'none';
      break;

    case 'connecting':
      statusMsg.textContent = state.message;
      mergeBtn.disabled = true;
      mergeBtn.className = 'merge-btn merging';
      mergeBtn.textContent = '⏳ Conectando...';
      progressContainer.style.display = 'block';
      progressBar.style.width = '20%';
      break;

    case 'merging':
      statusMsg.textContent = state.message;
      mergeBtn.disabled = true;
      mergeBtn.className = 'merge-btn merging';
      mergeBtn.textContent = '⏳ Uniendo...';
      progressContainer.style.display = 'block';
      progressBar.style.width = '60%';
      break;

    case 'complete':
      statusMsg.textContent = state.message;
      mergeBtn.disabled = false;
      mergeBtn.className = 'merge-btn complete';
      mergeBtn.textContent = '✅ Hecho';
      progressContainer.style.display = 'block';
      progressBar.style.width = '100%';
      break;

    case 'error':
      statusMsg.textContent = state.message;
      mergeBtn.disabled = false;
      mergeBtn.className = 'merge-btn error';
      mergeBtn.textContent = '🔁 Reintentar';
      progressContainer.style.display = 'none';
      break;
  }
}

function getState() {
  chrome.runtime.sendMessage({ type: 'GET_STATE' }, (state) => {
    if (state) updateUI(state);
  });
}

getState();

mergeBtn.addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'MERGE_VIDEOS' });
  statusMsg.textContent = 'Iniciando...';
  mergeBtn.disabled = true;
  mergeBtn.className = 'merge-btn merging';
  mergeBtn.textContent = '⏳ Uniendo...';
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'STATE_UPDATE') {
    updateUI(msg);
  }
});
