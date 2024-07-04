
const VisualHandler = require('./visualhandler');
const path = require('path');

module.exports = class ImageHandler extends VisualHandler {

    init(createMessage, resourcesPath) {
        super.init(createMessage, resourcesPath);
        const imgPath = `${resourcesPath}/${createMessage.asset}`;
        this.uiWrapper.innerHTML = `<img id = 'image-${this.id}' class = 'image-media' src = '${imgPath}'>`;
        this.name = path.parse(createMessage.asset).name;
        if (createMessage.displayName) {
            this.name = createMessage.displayName; // Override name
        }
    }

    getRegularUpdateState() {
        return {
            ...super.getRegularUpdateState(),
            effectType: 'image'
        };
    }

    getState() {
        return {
            ...super.getState(),
            effectType: 'image',
            name: this.name
        };
    }

    handleMessage(msg) {
        switch (msg.command) {
            default:
                return super.handleMessage(msg);
        }
    }

};
