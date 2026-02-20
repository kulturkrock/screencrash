function setupVideo(wrapper, message) {
  // TODO: Need to instruct users to allow autoplay. Can we check with javascript?
  const html = `
    <video id = 'video-${message.entityId}' class = 'video-media'>
    <audio id = 'audio-${message.entityId}' class = 'audio-media' src = '/api/stream/${message.streamId}/audio' preload = 'auto'>
  `;
  wrapper.innerHTML = html;

  const videoElement = wrapper.getElementsByTagName("video")[0];
  const audioElement = wrapper.getElementsByTagName("audio")[0];

  const videoSource = new MediaSource();
  videoElement.src = URL.createObjectURL(videoSource);
  videoSource.addEventListener("sourceopen", async () => {
    const sourceBuffer = videoSource.addSourceBuffer(
      'video/webm; codecs="vp9"',
    );
    sourceBuffer.mode = "sequence";

    const response = await fetch(`/api/stream/${message.streamId}/video`);
    if (!response.ok) {
      console.error(`Response status: ${response.status}`);
    }

    let currentBuffer = new Uint8Array(0);
    for await (const chunk of response.body) {
      console.log(`${new Date().toISOString()} Got ${chunk.byteLength}`);
      const newBuffer = new Uint8Array(
        currentBuffer.byteLength + chunk.byteLength,
      );
      newBuffer.set(currentBuffer, 0);
      newBuffer.set(chunk, currentBuffer.byteLength);
      currentBuffer = newBuffer;
      if (!sourceBuffer.updating) {
        console.log(`Writing ${currentBuffer.byteLength}`);
        sourceBuffer.appendBuffer(currentBuffer);
        currentBuffer = new Uint8Array(0);
      }
    }
  });

  setTimeout(() => {
    videoElement.play();
    audioElement.play();
  }, 1000);
}

export default { setupVideo };
