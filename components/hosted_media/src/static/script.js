import imageHandler from "./imageHandler.js";

function subscribe() {
    const eventSource = new EventSource("../api/subscribe");
    eventSource.addEventListener("message", event => {
        const message = JSON.parse(event.data);
        if (message.command === "create" && message.type === "image") {
            imageHandler.create(message);
        }
    })
}

subscribe();