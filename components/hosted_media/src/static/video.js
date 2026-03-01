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

function play(entityIdOrWrapper, time) {
  let wrapper;
  if (typeof entityIdOrWrapper === "string") {
    wrapper = document.getElementById(entityIdOrWrapper);
  } else {
    wrapper = entityIdOrWrapper;
  }
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

function syncTime(entityId, playoutTime, mediaTimeSeconds) {
  console.log(
    `Sync msg: ${mediaTimeSeconds}=${new Date(playoutTime).toISOString().split("T")[1].replace("Z", "")}`,
  );
  const wrapper = document.getElementById(entityId);
  if (wrapper === null) {
    return; // Element removed, ignore
  }
  const videoElement = wrapper.getElementsByTagName("video")[0];

  const syncInterval = setInterval(() => {
    const currentVideoTime = videoElement.currentTime;
    const now = performance.timeOrigin + performance.now();

    const projectedVideoTime = currentVideoTime + (playoutTime - now) / 1000; // May be in the past
    const videoDiff = projectedVideoTime - mediaTimeSeconds;
    console.log(`Video diff: ${videoDiff}`);
    if (videoDiff > 0.01) {
      videoElement.playbackRate = 0.99;
    } else if (videoDiff < -0.01) {
      videoElement.playbackRate = 1.01;
    } else {
      videoElement.playbackRate = 1;
    }
  }, 1000);
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
