let state = {
  deskshareUrl: null,
  webcamsUrl: null,
  cookies: '',
  status: 'idle',
  message: ''
};

let nativePort = null;

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg.type === 'VIDEOS_DETECTED') {
    state.deskshareUrl = msg.deskshareUrl;
    state.webcamsUrl = msg.webcamsUrl;
    state.cookies = msg.cookies || '';
    state.status = 'ready';
    chrome.action.setBadgeText({ text: '1' });
    chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
  }

  if (msg.type === 'GET_STATE') {
    return Promise.resolve({ ...state });
  }

  if (msg.type === 'MERGE_VIDEOS') {
    startMerge();
  }
});

function startMerge() {
  if (!state.deskshareUrl && !state.webcamsUrl) {
    state.status = 'error';
    state.message = 'No hay videos detectados. Abre una grabación BBB primero.';
    notifyPopup();
    return;
  }

  state.status = 'connecting';
  state.message = 'Conectando con el host nativo...';
  notifyPopup();

  try {
    nativePort = chrome.runtime.connectNative('com.bbb.merge');
  } catch (e) {
    state.status = 'error';
    state.message = 'Host nativo no encontrado. Ejecuta native-host/install.sh primero.';
    notifyPopup();
    return;
  }

  nativePort.onMessage.addListener((msg) => {
    switch (msg.type) {
      case 'ready':
        state.status = 'merging';
        state.message = 'Iniciando merge...';
        notifyPopup();
        nativePort.postMessage({
          type: 'merge',
          deskshareUrl: state.deskshareUrl,
          webcamsUrl: state.webcamsUrl,
          cookies: state.cookies
        });
        break;

      case 'progress':
        state.status = 'merging';
        state.message = msg.text || 'Procesando...';
        notifyPopup();
        break;

      case 'error':
        state.status = 'error';
        state.message = msg.text || 'Error desconocido';
        notifyPopup();
        cleanup();
        break;

      case 'complete':
        state.status = 'complete';
        state.message = msg.text || '¡Completado!';
        notifyPopup();
        chrome.action.setBadgeText({ text: '✓' });
        chrome.action.setBadgeBackgroundColor({ color: '#4CAF50' });
        cleanup();
        break;
    }
  });

  nativePort.onDisconnect.addListener(() => {
    if (chrome.runtime.lastError) {
      if (state.status !== 'complete' && state.status !== 'error') {
        state.status = 'error';
        state.message = 'Host nativo no encontrado. Revisa la instalación.';
        notifyPopup();
      }
    }
    cleanup();
  });
}

function cleanup() {
  if (nativePort) {
    try { nativePort.disconnect(); } catch (_) {}
    nativePort = null;
  }
}

function notifyPopup() {
  chrome.runtime.sendMessage({ type: 'STATE_UPDATE', ...state }).catch(() => {});
}
