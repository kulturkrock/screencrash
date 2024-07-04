
const VisualHandler = require('./visualhandler');

module.exports = class WebsiteHandler extends VisualHandler {

    init(createMessage, resourcesPath) {
        super.init(createMessage, resourcesPath);

        const urlPath = (createMessage.asset.startsWith('http')
            ? createMessage.asset
            : `${resourcesPath}/${createMessage.asset}`);

        this.uiWrapper.innerHTML = `
            <iframe id = "website-frame-${this.id}" class = "website-frame"
                    src = "${urlPath}"
                    frameborder = "0" height="100%" width="100%" scrolling = "no">
            </iframe>
        `;

        this.asset = createMessage.asset;
        this.name = createMessage.asset;
        if (createMessage.displayName) {
            this.name = createMessage.displayName; // Override name
        }
    }

    getRegularUpdateState() {
        return {
            ...super.getRegularUpdateState(),
            effectType: 'web'
        };
    }

    getState() {
        return {
            ...super.getState(),
            effectType: 'web',
            name: this.name
        };
    }

    handleMessage(msg) {
        switch (msg.command) {
            case 'refresh':
                this.refreshPage();
                break;
            default:
                return super.handleMessage(msg);
        }

        return true;
    }

    refreshPage() {
        const el = this.uiWrapper.getElementsByTagName('iframe')[0];
        if (el) {
            const operationChar = (this.asset.includes('?') ? '&' : '?');
            const randomString = (Math.random() + 1).toString(36).substring(7);
            const newPage = `${this.asset}${operationChar}screencrash_web_component_refresh_arg=${randomString}`;
            el.src = newPage;
        } else {
            this.emitWarning('Failed to refresh webpage');
        }
    }

};
