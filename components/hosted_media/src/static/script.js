import images from "./images.js";
import wrappers from "./wrappers.js";

function subscribe() {
  const eventSource = new EventSource("../api/subscribe");
  eventSource.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.command === "destroy") {
      destroy(message.entityId);
    } else if (message.command === "create" && message.type === "image") {
      wrappers.create(message, images.setupImage);
    } else if (message.command === "setVisible") {
      wrappers.setVisible(message.entityId, message.visible);
    } else if (message.command === "setOpacity") {
      wrappers.setOpacity(message.entityId, message.opacity);
    } else {
      console.error(
        `Unknown command '${message.command}' on type '${message.type}'`
      );
    }
  });
}

subscribe();
