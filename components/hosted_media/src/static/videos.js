function setupVideo(wrapper, message) {
  // TODO: Need to instruct users to allow autoplay. Can we check with javascript?
  const html = `
    <video id = 'video-${message.entityId}' class = 'video-media' autoplay src = '/api/stream/${message.streamId}/video'>
    <audio id = 'audio-${message.entityId}' class = 'audio-media' autoplay src = '/api/stream/${message.streamId}/audio'>
  `;

  wrapper.innerHTML = html;
}

export default { setupVideo };
