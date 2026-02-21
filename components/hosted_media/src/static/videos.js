function attachMediaSource(element, codec, url) {
  const mediaSource = new MediaSource();
  element.src = URL.createObjectURL(mediaSource);

  mediaSource.addEventListener("sourceopen", async () => {
    const sourceBuffer = mediaSource.addSourceBuffer(codec);
    sourceBuffer.mode = "sequence";

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
  // TODO: Need to instruct users to allow autoplay. Can we check with javascript?
  const html = `
    <video id = 'video-${message.entityId}' class = 'video-media'>
    <audio id = 'audio-${message.entityId}' class = 'audio-media'>
  `;
  wrapper.innerHTML = html;
  const videoElement = wrapper.getElementsByTagName("video")[0];
  const audioElement = wrapper.getElementsByTagName("audio")[0];
  if (message.startTime !== undefined) {
    const startTime = Date.parse(message.startTime);
    play(wrapper, startTime);
  }

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

  setTimeout(() => {
    console.log(`Started: ${Date.now()}`);
    videoElement.play();
    audioElement.play();
    tempIntervalId = setInterval(() => {
      console.log(
        `Current time: ${Date.now()}, audio: ${audioElement.currentTime}`,
      );
    }, 1000);
  }, time - Date.now());
}

function pause(entityId, time) {
  const wrapper = document.getElementById(entityId);
  const videoElement = wrapper.getElementsByTagName("video")[0];
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  setTimeout(() => {
    console.log(`Paused: ${Date.now()}`);
    videoElement.pause();
    audioElement.pause();
    clearInterval(tempIntervalId);
  }, time - Date.now());
}

export default { setupVideo, play, pause };
