(function () {
  'use strict';

  function findVideoSrcs() {
    const result = { deskshareUrl: null, webcamsUrl: null, cookies: document.cookie };
    const candidates = [];
    document.querySelectorAll('video').forEach(el => candidates.push(el));

    function check(url) {
      if (!url) return;
      try {
        const abs = new URL(url, document.baseURI).href;
        const path = abs.toLowerCase();

        if (!result.deskshareUrl &&
            path.includes('deskshare') &&
            (path.endsWith('.webm') || path.endsWith('.mp4'))) {
          result.deskshareUrl = abs;
          console.log('[BBB Merge] deskshare detectado:', abs);
        }

        if (!result.webcamsUrl &&
            path.includes('webcams') &&
            (path.endsWith('.webm') || path.endsWith('.mp4'))) {
          result.webcamsUrl = abs;
          console.log('[BBB Merge] webcams detectado:', abs);
        }
      } catch (_) {}
    }

    for (const video of candidates) {
      check(video.src);
      check(video.currentSrc);
      check(video.getAttribute('src'));
      check(video.getAttribute('data-src'));

      for (const source of video.querySelectorAll('source')) {
        check(source.src);
        check(source.getAttribute('src'));
      }
    }

    return result;
  }

  function sendVideos() {
    const videos = findVideoSrcs();
    if (videos.deskshareUrl || videos.webcamsUrl) {
      chrome.runtime.sendMessage({ type: 'VIDEOS_DETECTED', ...videos }).catch(() => {});
    }
  }

  sendVideos();

  [1000, 3000, 5000, 10000].forEach(d => setTimeout(sendVideos, d));

  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === 'childList' && m.addedNodes.length > 0) { sendVideos(); break; }
      if (m.type === 'attributes') { sendVideos(); break; }
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['src', 'data-src']
  });

  setTimeout(() => observer.disconnect(), 30000);

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'RESCAN') {
      sendVideos();
    }
  });
})();
