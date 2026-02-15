function setupVideo(wrapper, message) {
  // TODO: Need to instruct users to allow autoplay. Can we check with javascript?
  const html = `
    <video id = 'video-${message.entityId}' class = 'video-media' src = '/api/stream/${message.streamId}/video' preload = 'auto'>
    <audio id = 'audio-${message.entityId}' class = 'audio-media' src = '/api/stream/${message.streamId}/audio' preload = 'auto'>
  `;
  wrapper.innerHTML = html;
  setTimeout(() => {
    const video = document.getElementById(`video-${message.entityId}`).play();
    const audio = document.getElementById(`audio-${message.entityId}`).play();
  }, 1000);
}

export default { setupVideo };
