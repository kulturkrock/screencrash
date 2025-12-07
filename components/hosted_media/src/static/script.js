import imageHandler from "./imageHandler.js";

function destroy(entityId) {
    const wrapper = document.getElementById(entityId);
    wrapper.parentNode.removeChild(wrapper);
}

function subscribe() {
    const eventSource = new EventSource("../api/subscribe");
    eventSource.addEventListener("message", event => {
        const message = JSON.parse(event.data);
        if (message.command === "destroy") {
            destroy(message.entityId);
        } else if (message.command === "create" && message.type === "image") {
            imageHandler.create(message);
        }
    })
}

subscribe();