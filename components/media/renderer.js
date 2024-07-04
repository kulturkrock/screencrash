const { ipcRenderer } = require('electron');

const path = require('path');
const os = require('os');

// Workaround: On some computers the audio system may go to sleep and
// take a short while to activate. This can cut off the beginning of
// clips, so we "play" a looping silent sound to prevent this.
if (process.env.SCREENCRASH_NO_AUDIO !== 'true' && process.env.SCREENCRASH_DISABLE_AUDIO_WORKAROUND !== 'true') {
    const audioDiv = document.createElement('div');
    audioDiv.innerHTML = '<audio class="audio-media hidden" src="silence.wav" autoplay loop></audio>';
    document.body.appendChild(audioDiv);
}

// Init command handler
const CommandRouter = require('./model/commandrouter');
const FileHandler = require('./model/fileHandler');
const resourcesPath = path.join(__dirname, 'resources');
const fileHandler = new FileHandler(resourcesPath);
const commandRouter = new CommandRouter(document, fileHandler);

// Init connection to core
const Connection = require('./model/coreconnection');
const addr = `${process.env.SCREENCRASH_CORE || 'localhost:8001'}`;
const coreConnection = new Connection(
    `ws://${addr}/`,
    commandRouter.initialMessage.bind(commandRouter)
);
coreConnection.addEventListener('command', (event) => {
    commandRouter.handleMessage(event.detail);
});

const showDisconnectInfo = process.env.SCREENCRASH_DISCONNECT_INFO !== 'false';
if (showDisconnectInfo) {
    coreConnection.addEventListener('connected', () => {
        document.getElementById('disconnected').style.display = 'none';
    });
    coreConnection.addEventListener('disconnected', () => {
        document.getElementById('disconnected').style.display = 'block';
    });

    document.getElementById('disconnected_addr').innerHTML = addr;
    document.getElementById('disconnected_local_addr').innerHTML = getLocalIP();
} else {
    document.getElementById('disconnected').style.display = 'none';
}

commandRouter.init(coreConnection.send.bind(coreConnection));
commandRouter.addEventListener('relaunch', () => {
    ipcRenderer.send('relaunch-app');
});

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
