
module.exports = class Model {

    constructor(dom) {
        this.dom = dom;
        this.componentId =
            process.env.SCREENCRASH_COMPONENT_ID ||
            crypto.randomBytes(8).toString('hex');
        this.getInitialMessage = this.getInitialMessage.bind(this);
        this.broken = [];
        this.sendFunction = null;
        this.update();
    }

    init(_sendFunction) {
        this.sendFunction = _sendFunction;
    }

    sendLogMessage(level, content) {
        if (this.sendFunction) {
            this.sendFunction({
                messageType: 'log-message',
                level: level,
                msg: content
            });
        }
    }

    getInitialMessage() {
        return {
            type: 'announce',
            client: 'myggcheck',
            channel: 1
        };
    }

    handleMessage(msg) {
        console.log(`Got message ${JSON.stringify(msg)}`);
        switch (msg.command) {
            case "broken":
                if (!msg.name) {
                    this.sendLogMessage('warning', 'Cannot set unnamed mygga to BROKEN');
                    break;
                }
                if (!this.broken.includes(msg.name)) {
                    this.broken.push(msg.name);
                    this.update();
                }
                break;
            case "fixed":
                if (!msg.name) {
                    this.sendLogMessage('warning', 'Cannot set unnamed mygga to FIXED');
                    break;
                }
                this.broken = this.broken.filter(x => x !== msg.name);
                this.update();
                break;
            case "reset":
                this.broken = [];
                this.update();
                break;
            case 'req_component_info':
                console.log("Got request for info");
                if (this.sendFunction) {
                    this.sendFunction({
                        messageType: 'component_info',
                        componentId: this.componentId,
                        componentName: 'myggcheck',
                        status: 'online'
                    });
                }
                break;
        }
    }

    update() {
        console.log(`Updating with broken = ${this.broken}`);
        const parentElement = this.dom.getElementById('content');
        const isOk = this.broken.length === 0;
        if (this.broken.length === 0) {
            parentElement.innerHTML = "<div class = 'container ok'><div class='containercontent'>Alla myggor är glada</div></div>";
        } else {
            const myggInfo = this.broken.map(m => {
                return `<div class = 'mygginfo'>${m}</div>`;
            }).join("");
            parentElement.innerHTML = `<div class = 'container notok'><div class='containercontent'>Trasiga myggor: ${myggInfo}</div></div>`;
        }
    }

}