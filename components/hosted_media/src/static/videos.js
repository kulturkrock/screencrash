function setupVideo(wrapper, message) {
  // TODO: Need to instruct users to allow autoplay. Can we check with javascript?
  // TODO: Also need the audio workaround from the old media
  const html = `<video id = 'video-${message.entityId}' class = 'video-media' autoplay src = '/api/stream/${message.entityId}'>`;
  wrapper.innerHTML = html;
}

export default { setupVideo };
