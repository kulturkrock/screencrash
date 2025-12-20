import domUtils from "./domUtils.js";

function create(message, setupFunction) {
  const wrapper = document.createElement("div");
  wrapper.id = message.entityId;

  wrapper.className = "media-wrapper hidden";
  _setVisible(wrapper, message.visible);
  _setOpacity(wrapper, message.opacity, message.fadeIn);
  _setViewport(
    wrapper,
    message.x,
    message.y,
    message.width,
    message.height,
    message.usePercentage
  );
  _setLayer(wrapper, message.layer);
  setupFunction(wrapper, message);

  document.body.appendChild(wrapper);
}

function destroy(entityId) {
  const wrapper = document.getElementById(entityId);
  wrapper.parentNode.removeChild(wrapper);
}

function _setVisible(wrapper, visible) {
  if (visible) {
    domUtils.removeClass(wrapper, "hidden");
  } else {
    domUtils.addClass(wrapper, "hidden");
  }
}

function setVisible(entityId, visible) {
  const wrapper = document.getElementById(entityId);
  _setVisible(wrapper, visible);
}

function _setOpacity(wrapper, opacity, fadeIn) {
  if (fadeIn !== undefined) {
    // First, set initial opacity
    wrapper.style.opacity = fadeIn.from;
    // Then schedule setting the transition and target opacity 1ms in the future
    setTimeout(() => {
      wrapper.style.transition = `opacity ${fadeIn.time}s linear`;
      wrapper.style.opacity = fadeIn.to;
      // Finally, schedule cleaning up the transition when it's done, so it doesn't affect future opacity changes
      setTimeout(() => {
        wrapper.style.transition = "";
      }, fadeIn.time * 1000);
    }, 1);
  } else {
    wrapper.style.opacity = opacity;
  }
}

function setOpacity(entityId, opacity) {
  const wrapper = document.getElementById(entityId);
  _setOpacity(wrapper, opacity);
}

function _setViewport(wrapper, x, y, width, height, usePercentage) {
  const suffix = usePercentage ? "%" : "px";

  if (x !== null) {
    wrapper.style.left = x + suffix;
  } else {
    wrapper.style.left = "0%";
  }
  if (y !== null) {
    wrapper.style.top = y + suffix;
  } else {
    wrapper.style.top = "0%";
  }
  if (width !== null) {
    wrapper.style.width = width + suffix;
  } else {
    wrapper.style.width = "100%";
  }
  if (height !== null) {
    wrapper.style.height = height + suffix;
  } else {
    wrapper.style.height = "100%";
  }
}

function setViewport(entityId, x, y, width, height, usePercentage) {
  const wrapper = document.getElementById(entityId);
  _setViewport(wrapper, x, y, width, height, usePercentage);
}

function _setLayer(wrapper, layer) {
  wrapper.style.zIndex = layer;
}

function setLayer(entityId, layer) {
  const wrapper = document.getElementById(entityId);
  _setLayer(wrapper, layer);
}

function fade(entityId, fadeTo, time) {
  const wrapper = document.getElementById(entityId);
  wrapper.style.transition = `opacity ${time}s linear`;
  wrapper.style.opacity = fadeTo;
  // Clean up the transition so it doesn't affect future opacity changes
  setTimeout(() => (wrapper.style.transition = ""), time * 1000);
}

export default {
  create,
  destroy,
  setVisible,
  setOpacity,
  setViewport,
  setLayer,
  fade,
};
