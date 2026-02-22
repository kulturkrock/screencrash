import images from "./images.js";
import videos from "./videos.js";
import wrappers from "./wrappers.js";
import domUtils from "./domUtils.js";

function subscribe() {
  const eventSource = new EventSource("../api/subscribe");
  eventSource.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.command === "destroy") {
      wrappers.destroy(
        message.entityId,
        message.time ? Date.parse(message.time) : null,
      );
    } else if (message.command === "create" && message.type === "image") {
      wrappers.create(message, images.setupImage);
    } else if (message.command === "create" && message.type === "video") {
      wrappers.create(message, videos.setupVideo);
    } else if (message.command === "setVisible") {
      wrappers.setVisible(message.entityId, message.visible);
    } else if (message.command === "setOpacity") {
      wrappers.setOpacity(message.entityId, message.opacity);
    } else if (message.command === "setViewport") {
      wrappers.setViewport(
        message.entityId,
        message.x,
        message.y,
        message.width,
        message.height,
        message.usePercentage,
      );
    } else if (message.command === "setLayer") {
      wrappers.setLayer(message.entityId, message.layer);
    } else if (message.command === "fade") {
      wrappers.fade(message.entityId, message.to, message.time);
    } else if (message.command === "play") {
      videos.play(message.entityId, Date.parse(message.time));
    } else if (message.command === "pause") {
      videos.pause(message.entityId, Date.parse(message.time));
    } else if (message.command === "mute") {
      videos.setMuted(message.entityId, true);
    } else if (message.command === "unmute") {
      videos.setMuted(message.entityId, false);
    } else if (message.command === "setVolume") {
      videos.setVolume(message.entityId, message.volume);
    } else {
      console.error(
        `Unknown command '${message.command}' on type '${message.type}'`,
      );
    }
  });
}

async function playAudioKeepalive() {
  const audioElement = document.getElementById("audio-keepalive");
  try {
    await audioElement.play();
  } catch {
    const textElement = document.createElement("div");
    textElement.textContent =
      "Autoplay är blockerat, ge den här sidan tillstånd att spela ljud i webbläsarens inställningar.";
    domUtils.addClass(textElement, "autoplay-warning");
    document.body.appendChild(textElement);
  }
}

playAudioKeepalive();
subscribe();
