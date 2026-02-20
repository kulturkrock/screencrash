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
  attachMediaSource(
    videoElement,
    'video/webm; codecs="vp9"',
    `/api/stream/${message.streamId}/video`,
  );

  const audioElement = wrapper.getElementsByTagName("audio")[0];
  attachMediaSource(
    audioElement,
    'audio/webm; codecs="opus"',
    `/api/stream/${message.streamId}/audio`,
  );

  const startTime = Date.parse(message.startTime);
  setTimeout(() => {
    videoElement.play();
    audioElement.play();
  }, startTime - Date.now());
}

export default { setupVideo };
