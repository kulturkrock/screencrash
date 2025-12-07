
async function getState() {
    const response = await fetch("../api/state");
    const state = await response.json();
    document.getElementById("state").textContent = "Senast skapad: " + state.last_created;
}

getState();