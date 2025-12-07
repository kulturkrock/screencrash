function create(message, setupFunction) {
  const wrapper = document.createElement("div");
  wrapper.id = message.entityId;
  if (message.visible) {
    wrapper.className = "media-wrapper";
  } else {
    wrapper.className = "media-wrapper hidden";
  }
  setupFunction(wrapper, message);

  document.body.appendChild(wrapper);
}

function destroy(entityId) {
  const wrapper = document.getElementById(entityId);
  wrapper.parentNode.removeChild(wrapper);
}

function setVisible(entityId, visible) {
  const wrapper = document.getElementById(entityId);
  if (visible) {
    domUtils.removeClass(wrapper, "hidden");
  } else {
    domUtils.addClass(wrapper, "hidden");
  }
}

export default { create, destroy, setVisible };
