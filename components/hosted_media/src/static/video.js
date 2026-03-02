import util from "./util.js";

function attachMediaSource(element, codec, url) {
  const mediaSource = new MediaSource();
  element.src = URL.createObjectURL(mediaSource);

  mediaSource.addEventListener("sourceopen", async () => {
    const sourceBuffer = mediaSource.addSourceBuffer(codec);
    sourceBuffer.mode = "sequence";
    // We fetch data ourselves instead of giving the URL to the audio/video element
    // because the element doesn't fetch data aggressively enough, which leads to
    // stuttering
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`Response status: ${response.status}`);
    }

    let currentBuffer = new Uint8Array(0);
    for await (const chunk of response.body) {
      const newBuffer = new Uint8Array(
        currentBuffer.byteLength + chunk.byteLength,
      );
      newBuffer.set(currentBuffer, 0);
      newBuffer.set(chunk, currentBuffer.byteLength);
      currentBuffer = newBuffer;
      if (!sourceBuffer.updating) {
        sourceBuffer.appendBuffer(currentBuffer);
        currentBuffer = new Uint8Array(0);
      }
    }
  });
}

function setupVideo(wrapper, message) {
  const videoElement = document.createElement("video");
  videoElement.id = `video-${message.entityId}`;
  videoElement.className = "video-media";
  wrapper.appendChild(videoElement);

  attachMediaSource(
    videoElement,
    'video/webm; codecs="vp9"',
    `/api/stream/${message.streamId}/video`,
  );
}

function play(entityId, time) {
  const wrapper = document.getElementById(entityId);
  const videoElement = wrapper.getElementsByTagName("video")[0];

  util.doAtTime(time, () => {
    videoElement.play();
  });
}

function pause(entityId, time) {
  const wrapper = document.getElementById(entityId);
  const videoElement = wrapper.getElementsByTagName("video")[0];

  util.doAtTime(time, () => {
    videoElement.pause();
  });
}

function formatDiff(diff) {
  const diffInMs = Math.round(diff * 1000);
  if (diffInMs >= 0) {
    return `${diffInMs}ms ahead of target`;
  } else {
    return `${-diffInMs}ms behind target`;
  }
}

function syncTime(entityId, playoutTime, mediaTimeSeconds) {
  console.info(
    `Got video sync message for '${entityId}': ${mediaTimeSeconds}=${new Date(playoutTime).toISOString().split("T")[1].replace("Z", "")}`,
  );
  const wrapper = document.getElementById(entityId);
  if (wrapper === null) {
    return; // Element removed, ignore
  }
  const videoElement = wrapper.getElementsByTagName("video")[0];

  // First log, just for troubleshooting
  const currentVideoTime = videoElement.currentTime;
  const now = performance.timeOrigin + performance.now();

  const projectedVideoTime = currentVideoTime + (playoutTime - now) / 1000; // May be in the past
  const videoDiff = projectedVideoTime - mediaTimeSeconds;
  console.info(`Video '${entityId}' is ${formatDiff(videoDiff)}.`);

  const syncInterval = setInterval(() => {
    const currentVideoTime = videoElement.currentTime;
    const now = performance.timeOrigin + performance.now();

    const projectedVideoTime = currentVideoTime + (playoutTime - now) / 1000; // May be in the past
    const videoDiff = projectedVideoTime - mediaTimeSeconds;
    if (videoDiff > 0.01) {
      console.info(
        `Video '${entityId}' is ${formatDiff(videoDiff)}. Playing slightly slower.`,
      );
      videoElement.playbackRate = 0.99;
    } else if (videoDiff < -0.01) {
      console.info(
        `Video '${entityId}' is ${formatDiff(videoDiff)}. Playing slightly faster.`,
      );
      videoElement.playbackRate = 1.01;
    } else {
      if (videoElement.playbackRate !== 1) {
        console.info(
          `Video '${entityId}' is ${formatDiff(videoDiff)}. Playing at normal speed.`,
        );
        videoElement.playbackRate = 1;
      }
    }
  }, 500);
  setTimeout(() => {
    clearInterval(syncInterval);
    videoElement.playbackRate = 1;
  }, 10 * 1000);
}

export default {
  setupVideo,
  play,
  pause,
  syncTime,
};
