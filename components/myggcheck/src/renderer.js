const { ipcRenderer } = require('electron');

const path = require('path');
const os = require('os');

// Init connection to core
const Connection = require('./coreconnection');
const Model = require('./model');
const model = new Model(document);
const addr = `${process.env.SCREENCRASH_CORE || 'localhost:8001'}`;
const coreConnection = new Connection(
    `ws://${addr}/`,
    model.getInitialMessage
);
model.init(coreConnection.send);
coreConnection.addEventListener('command', (event) => {
    if (event.detail.command === "restart") {
        ipcRenderer.send('relaunch-app');
    } else {
        model.handleMessage(event.detail);
    }
});

coreConnection.addEventListener('connected', () => {
    document.getElementById('disconnected').style.display = 'none';
    document.getElementById('content').style.display = 'block';
});
coreConnection.addEventListener('disconnected', () => {
    document.getElementById('disconnected').style.display = 'block';
    document.getElementById('content').style.display = 'none';
});

document.getElementById('disconnected_addr').innerHTML = addr;
document.getElementById('disconnected_local_addr').innerHTML = getLocalIP();

function getLocalIP() {
    const interfaces = os.networkInterfaces();
    for (const interfaceName in interfaces) {
        for (const address of interfaces[interfaceName]) {
            if (address.family === 'IPv4' && !address.internal) {
                return address.address;
            }
        }
    }

    return '[Unknown]';
}
