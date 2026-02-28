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

  audioElement.addEventListener("ended", () =>
    console.log(`Ended ${Date.now()}`),
  );
}

// Temporary, will not work if there are multiple videos at the same time
let tempIntervalId;

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
    console.log(`Started: ${Date.now()}`);
    videoElement.play();
    audioElement.play();
    tempIntervalId = setInterval(() => {
      console.log(
        `Current time: ${Date.now()}, audio: ${audioElement.currentTime}`,
      );
    }, 1000);
  });
}

function pause(entityId, time) {
  const wrapper = document.getElementById(entityId);
  const videoElement = wrapper.getElementsByTagName("video")[0];
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  util.doAtTime(time, () => {
    console.log(`Paused: ${Date.now()}`);
    videoElement.pause();
    audioElement.pause();
    clearInterval(tempIntervalId);
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

export default { setupVideo, play, pause, setMuted, setVolume, fadeAudio };
