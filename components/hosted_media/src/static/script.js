
async function subscribe() {
    const eventSource = new EventSource("../api/subscribe");
    eventSource.addEventListener("message", event => {
        const message = JSON.parse(event.data);
        document.getElementById("state").textContent = "Senast skapad: " + message.entityId;
    })
}

subscribe();