function setupImage(wrapper, message) {
  const html = `<img id = 'image-${message.entityId}' class = 'image-media' src = '/assets/${message.asset}'>`;
  wrapper.innerHTML = html;
}

export default { setupImage };
