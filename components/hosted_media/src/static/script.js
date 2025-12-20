import images from "./images.js";
import videos from "./videos.js";
import wrappers from "./wrappers.js";

function subscribe() {
  const eventSource = new EventSource("../api/subscribe");
  eventSource.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.command === "destroy") {
      wrappers.destroy(message.entityId);
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
        message.usePercentage
      );
    } else if (message.command === "setLayer") {
      wrappers.setLayer(message.entityId, message.layer);
    } else if (message.command === "fade") {
      wrappers.fade(
        message.entityId,
        message.to,
        message.time,
        message.destroyOnEnd
      );
    } else {
      console.error(
        `Unknown command '${message.command}' on type '${message.type}'`
      );
    }
  });
}

subscribe();
