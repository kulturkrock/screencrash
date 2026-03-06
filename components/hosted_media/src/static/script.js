import images from "./images.js";
import video from "./video.js";
import audio from "./audio.js";
import wrappers from "./wrappers.js";
import domUtils from "./domUtils.js";

const searchParams = new URLSearchParams(window.location.search);
const noVideo = searchParams.has("noVideo");
const noAudio = searchParams.has("noAudio");

function subscribe() {
  const eventSource = new EventSource("../api/subscribe");
  eventSource.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.command === "destroy") {
      if (wrappers.exists(message.entityId)) {
        wrappers.destroy(
          message.entityId,
          message.time ? Date.parse(message.time) : null,
        );
      }
    } else if (
      message.command === "create" &&
      message.type === "image" &&
      !noVideo
    ) {
      wrappers.create(message, images.setupImage);
    } else if (message.command === "create" && message.type === "video") {
      const setup = [];
      if (!noVideo) {
        setup.push(video.setupVideo);
      }
      if (!noAudio) {
        setup.push(audio.setupAudio);
      }
      wrappers.create(message, ...setup);
    } else if (
      message.command === "create" &&
      message.type === "audio" &&
      !noAudio
    ) {
      wrappers.create(message, audio.setupAudio);
    } else if (message.command === "setVisible") {
      if (wrappers.exists(message.entityId)) {
        wrappers.setVisible(message.entityId, message.visible);
      }
    } else if (message.command === "setOpacity") {
      if (wrappers.exists(message.entityId)) {
        wrappers.setOpacity(message.entityId, message.opacity);
      }
    } else if (message.command === "setViewport") {
      if (wrappers.exists(message.entityId)) {
        wrappers.setViewport(
          message.entityId,
          message.x,
          message.y,
          message.width,
          message.height,
          message.usePercentage,
        );
      }
    } else if (message.command === "setLayer") {
      if (wrappers.exists(message.entityId)) {
        wrappers.setLayer(message.entityId, message.layer);
      }
    } else if (message.command === "fade") {
      if (wrappers.exists(message.entityId)) {
        wrappers.fade(
          message.entityId,
          message.to,
          message.time,
          message.fadeStartTime ? Date.parse(message.fadeStartTime) : null,
        );
      }
      if (audio.exists(message.entityId)) {
        audio.fadeAudio(
          message.entityId,
          message.to,
          message.time,
          message.fadeStartTime ? Date.parse(message.fadeStartTime) : null,
        );
      }
    } else if (message.command === "play") {
      if (video.exists(message.entityId)) {
        video.play(message.entityId, Date.parse(message.time));
      }
      if (audio.exists(message.entityId)) {
        audio.play(message.entityId, Date.parse(message.time));
      }
    } else if (message.command === "pause") {
      if (video.exists(message.entityId)) {
        video.pause(
          message.entityId,
          Date.parse(message.time),
          message.pauseTimeInStream,
        );
      }
      if (audio.exists(message.entityId)) {
        audio.pause(
          message.entityId,
          Date.parse(message.time),
          message.pauseTimeInStream,
        );
      }
    } else if (message.command === "mute") {
      if (audio.exists(message.entityId)) {
        audio.setMuted(message.entityId, true);
      }
    } else if (message.command === "unmute") {
      if (audio.exists(message.entityId)) {
        audio.setMuted(message.entityId, false);
      }
    } else if (message.command === "setVolume") {
      if (audio.exists(message.entityId)) {
        audio.setVolume(message.entityId, message.volume);
      }
    } else if (message.command === "syncTime") {
      if (video.exists(message.entityId)) {
        video.syncTime(
          message.entityId,
          Date.parse(message.playoutTime),
          message.mediaTimeSeconds,
        );
      }
      if (audio.exists(message.entityId)) {
        audio.syncTime(
          message.entityId,
          Date.parse(message.playoutTime),
          message.mediaTimeSeconds,
        );
      }
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
if (!noAudio) {
  playAudioKeepalive();
}
subscribe();
