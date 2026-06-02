(function () {
  'use strict';

  function findVideoSrcs() {
    const result = { deskshareUrl: null, webcamsUrl: null, cookies: document.cookie };
    const videos = document.querySelectorAll('video');

    function check(url) {
      if (!url) return;
      try {
        const abs = new URL(url, document.baseURI).href;
        if (abs.includes('deskshare') && abs.endsWith('.webm') && !result.deskshareUrl) {
          result.deskshareUrl = abs;
        }
        if (abs.includes('webcams') && abs.endsWith('.webm') && !result.webcamsUrl) {
          result.webcamsUrl = abs;
        }
      } catch (_) {}
    }

    for (const video of videos) {
      check(video.src || video.currentSrc);
      for (const source of video.querySelectorAll('source')) {
        check(source.src);
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', sendVideos);
  } else {
    sendVideos();
  }

  setTimeout(sendVideos, 3000);

  const observer = new MutationObserver(() => sendVideos());
  observer.observe(document.body, { childList: true, subtree: true });
  setTimeout(() => observer.disconnect(), 15000);
})();
