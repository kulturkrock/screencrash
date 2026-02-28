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
  const html = `
    <video id = 'video-${message.entityId}' class = 'video-media'>
    <audio id = 'audio-${message.entityId}' class = 'audio-media'>
  `;
  wrapper.innerHTML = html;
  const videoElement = wrapper.getElementsByTagName("video")[0];
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  audioElement.muted = message.muted;
  audioElement.volume = message.volume / 100;
  audioElement.preservesPitch = false; // TODO: Is this worth it?

  attachMediaSource(
    videoElement,
    'video/webm; codecs="vp9"',
    `/api/stream/${message.streamId}/video`,
  );

  attachMediaSource(
    audioElement,
    'audio/webm; codecs="opus"',
    `/api/stream/${message.streamId}/audio`,
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
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  util.doAtTime(time, () => {
    videoElement.play();
    audioElement.play();
  });
}

function pause(entityId, time) {
  const wrapper = document.getElementById(entityId);
  const videoElement = wrapper.getElementsByTagName("video")[0];
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  util.doAtTime(time, () => {
    videoElement.pause();
    audioElement.pause();
  });
}

function setMuted(entityId, muted) {
  const wrapper = document.getElementById(entityId);
  const audioElement = wrapper.getElementsByTagName("audio")[0];
  audioElement.muted = muted;
}

function setVolume(entityId, volume) {
  const wrapper = document.getElementById(entityId);
  const audioElement = wrapper.getElementsByTagName("audio")[0];
  audioElement.volume = volume / 100;
}

function fadeAudio(entityId, toVolume, duration, fadeStartTime) {
  const wrapper = document.getElementById(entityId);
  util.doAtTime(fadeStartTime, () => {
    doFade(wrapper, toVolume, duration);
  });
}

function doFade(wrapper, toVolume, duration) {
  // Here toVolume is between 0 and 1, not 0 and 100
  const audioElement = wrapper.getElementsByTagName("audio")[0];
  const startingVolume = audioElement.volume;
  const stepTime = 50;
  const volumeStep =
    (toVolume - startingVolume) / ((duration * 1000) / stepTime);
  const intervalId = setInterval(() => {
    const newVolume = audioElement.volume + volumeStep;
    if (newVolume <= 0) {
      audioElement.volume = 0;
      clearInterval(intervalId);
    } else {
      audioElement.volume = newVolume;
    }
  }, stepTime);
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
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  const syncInterval = setInterval(() => {
    const currentAudioTime = audioElement.currentTime;
    const currentVideoTime = videoElement.currentTime;
    const now = performance.timeOrigin + performance.now();
    const projectedAudioTime = currentAudioTime + (playoutTime - now) / 1000; // May be in the past
    const audioDiff = projectedAudioTime - mediaTimeSeconds;
    console.log(`Audio diff: ${audioDiff}`);
    if (audioDiff > 0.01) {
      audioElement.playbackRate = 0.995;
    } else if (audioDiff < -0.01) {
      audioElement.playbackRate = 1.005;
    } else {
      audioElement.playbackRate = 1;
    }

    const projectedVideoTime = currentVideoTime + (playoutTime - now) / 1000; // May be in the past
    const videoDiff = projectedVideoTime - mediaTimeSeconds;
    console.log(`Video diff: ${videoDiff}`);
    if (videoDiff > 0.01) {
      videoElement.playbackRate = 0.99;
    } else if (audioDiff < -0.01) {
      videoElement.playbackRate = 1.01;
    } else {
      videoElement.playbackRate = 1;
    }
  }, 1000);
  setTimeout(() => {
    clearInterval(syncInterval);
    audioElement.playbackRate = 1;
    videoElement.playbackRate = 1;
  }, 10 * 1000);
}

export default {
  setupVideo,
  play,
  pause,
  setMuted,
  setVolume,
  fadeAudio,
  syncTime,
};
