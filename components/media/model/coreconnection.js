
module.exports = class CoreConnection extends EventTarget {

    constructor(address, getAnnounceMessage = null, reconnect = true, reconnectWait = 3000) {
        super();
        this.address = address;
        this.getAnnounceMessage = getAnnounceMessage;
        this.reconnect = reconnect;
        this.reconnectWait = reconnectWait;
        this.socket = null;
        this.heartbeatInterval = null;
        this.connect();
    }

    connect() {
        if (this.heartbeatInterval != null) {
            clearInterval(this.heartbeatInterval);
        }

        this.socket = new WebSocket(this.address);
        this.socket.addEventListener('open', this.onConnected.bind(this));
        this.socket.addEventListener('message', this.onMessage.bind(this));
        this.socket.addEventListener('close', this.onDisconnected.bind(this));

        // TODO: Adjust time according to spec
        this.heartbeatInterval = setInterval(this._sendHeartbeat.bind(this), 1000);
    }

    send(dataObj) {
        if (this.socket) {
            this.socket.send(JSON.stringify(dataObj));
        }
    }

    async onConnected(event) {
        console.log('Connected to server: ' + event.target.url);
        if (this.getAnnounceMessage) {
            this.send(await this.getAnnounceMessage());
        }
        this.dispatchEvent(new CustomEvent('connected'));
    }

    onMessage(event) {
        const msg = JSON.parse(event.data);
        if (msg != null) {
            this.dispatchEvent(new CustomEvent('command', { detail: msg }));
        } else {
            console.log('Warning: Got badly formatted message');
        }
    }

    onDisconnected() {
        this.socket = null;
        if (this.reconnect) {
            console.log('Trying to reconnect in %d ms', this.reconnectWait);
            setTimeout(this.connect.bind(this), this.reconnectWait);
        } else {
            console.log('Unexpectedly lost connection');
        }
        this.dispatchEvent(new CustomEvent('disconnected'));
    }

    _getHeartbeatMessage() {
        return {
            messageType: 'heartbeat',
            component: 'media',
            channel: 1
        };
    }

    _sendHeartbeat() {
        if (this.socket != null && this.socket.readyState === WebSocket.OPEN) {
            this.send(this._getHeartbeatMessage());
        }
    }

};
