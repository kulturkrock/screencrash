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

function setupAudio(wrapper, message) {
  const audioElement = document.createElement("audio");
  audioElement.id = `audio-${message.entityId}`;
  audioElement.className = "audio-media";
  wrapper.appendChild(audioElement);

  audioElement.muted = message.muted;
  audioElement.volume = message.volume / 100;
  // Prevents audio popping when changing playbackSpeed to sync times.
  // But we need to keep playbackSpeed close to 1 or we will hear the change in pitch!
  audioElement.preservesPitch = false;

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
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  // Start a little earlier to account for delays in the browser.
  // Not exact, but will be synced more finely later.
  util.doAtTime(time - 80, () => {
    audioElement.play();
  });
}

function pause(entityId, time) {
  const wrapper = document.getElementById(entityId);
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  util.doAtTime(time, () => {
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
    `Got audio sync message for ${entityId}: ${mediaTimeSeconds}=${new Date(playoutTime).toISOString().split("T")[1].replace("Z", "")}`,
  );
  const wrapper = document.getElementById(entityId);
  if (wrapper === null) {
    return; // Element removed, ignore
  }
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  // First log, just for troubleshooting
  const currentAudioTime = audioElement.currentTime;
  const now = performance.timeOrigin + performance.now();

  const projectedAudioTime = currentAudioTime + (playoutTime - now) / 1000; // May be in the past
  const audioDiff = projectedAudioTime - mediaTimeSeconds;
  console.info(`Audio '${entityId}' is ${formatDiff(audioDiff)}.`);

  const syncInterval = setInterval(() => {
    const currentAudioTime = audioElement.currentTime;
    const now = performance.timeOrigin + performance.now();
    const projectedAudioTime = currentAudioTime + (playoutTime - now) / 1000; // May be in the past
    const audioDiff = projectedAudioTime - mediaTimeSeconds;
    // Minimum discernable difference in pitch seems to be around 0.5%
    // https://music.stackexchange.com/a/122645
    if (audioDiff > 0.01) {
      console.info(
        `Audio '${entityId}' is ${formatDiff(audioDiff)}. Playing slightly slower.`,
      );
      audioElement.playbackRate = 0.995;
    } else if (audioDiff < -0.01) {
      console.info(
        `Audio '${entityId}' is ${formatDiff(audioDiff)}. Playing slightly faster.`,
      );
      audioElement.playbackRate = 1.005;
    } else {
      if (audioElement.playbackRate !== 1) {
        console.info(
          `Audio '${entityId}' is ${formatDiff(audioDiff)}. Playing at normal speed.`,
        );
        audioElement.playbackRate = 1;
      }
    }
  }, 500);
  setTimeout(() => {
    clearInterval(syncInterval);
    audioElement.playbackRate = 1;
  }, 10 * 1000);
}

export default {
  setupAudio,
  play,
  pause,
  setMuted,
  setVolume,
  fadeAudio,
  syncTime,
};
