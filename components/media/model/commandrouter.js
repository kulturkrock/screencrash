const crypto = require('crypto');
const VideoHandler = require('./media/videohandler');
const ImageHandler = require('./media/imagehandler');
const WebsiteHandler = require('./media/websitehandler');
const AudioHandler = require('./media/audiohandler');

module.exports = class CommandRouter extends EventTarget {

    constructor(dom, fileHandler) {
        super();
        this.componentId =
            process.env.SCREENCRASH_COMPONENT_ID ||
            crypto.randomBytes(8).toString('hex');
        this.supportedTypes =
            process.env.SCREENCRASH_SUPPORTED_TYPES ||
            this.getDefaultSupportedTypes();
        this.dom = dom;
        this.fileHandler = fileHandler;
        this.handlers = {};
        this.regularUpdateInterval = setInterval(this._regularUpdate.bind(this), 500);
    }

    getDefaultSupportedTypes() {
        if (process.env.SCREENCRASH_NO_WINDOW === 'true' && process.env.SCREENCRASH_NO_AUDIO === 'true') {
            return [];
        } else if (process.env.SCREENCRASH_NO_WINDOW === 'true') {
            return ['audio', 'video'];
        } else if (process.env.SCREENCRASH_NO_AUDIO === 'true') {
            return ['video', 'image', 'web'];
        } else {
            return ['audio', 'video', 'image', 'web'];
        }
    }

    async initialMessage() {
        return {
            type: 'announce',
            client: 'media',
            channel: 1
        };
    }

    init(sendFunction) {
        this.sendFunction = sendFunction;
    }

    async reportChecksums() {
        this.sendFunction({ messageType: 'file_checksums', files: await this.fileHandler.getHashes() });
    }

    logMessage(data) {
        if (this.sendFunction) {
            console.log(`Got ${data.level} message: ${data.message}`);
            this.sendFunction({
                messageType: 'log-message',
                level: data.level,
                msg: data.message
            });
        } else {
            console.log(`${data.level}: ${data.message}`);
        }
    }

    reportWarning(msg) {
        this.logMessage({ level: 'warning', message: msg });
    }

    reportError(msg) {
        this.logMessage({ level: 'error', message: msg });
    }

    handleMessage(msg) {
        // Log occurrence
        // console.log('CommandHandler got message: ' + JSON.stringify(msg));

        if (msg.type && !(this.supportedTypes.includes(msg.type))) {
            // We have disabled this media type on this instance of
            // this component. Ignore commands regarding it.
            console.log(`Supported types: ${this.supportedTypes} msg.type=${msg.type}`);
            console.log(`Skipping message due to not supported type ${JSON.stringify(msg, null, 4)}`);
            return;
        }

        // Handle creation and destruction of handlers, delegate all else.
        try {
            switch (msg.command) {
                case 'req_component_info':
                    this.sendFunction({
                        messageType: 'component_info',
                        ...this.getComponentInfo()
                    });
                    break;
                case 'create':
                    this.createHandler(msg);
                    break;
                case 'destroy':
                    this.destroyHandler(msg.entityId);
                    break;
                case 'reset':
                    this.resetAll();
                    break;
                case 'restart':
                    this.restart();
                    break;
                case 'file':
                    this.fileHandler.writeFile(msg);
                    break;
                case 'report_checksums':
                    this.reportChecksums();
                    break;
                default:
                    this.sendMessageToHandler(msg.entityId, msg);
                    break;
            }
        } catch (e) {
            this.reportError(`Failed command: ${e}`);
        }
    }

    createHandler(msg) {
        const entityId = msg.entityId;

        if (entityId in this.handlers) {
            this.reportWarning(`A handler for entity id ${entityId} was overwritten by a new one`);
            this.destroyHandler(entityId);
        }

        this.handlers[entityId] = this.createHandlerFromType(entityId, msg.type);
        this.handlers[entityId].init(msg, this.fileHandler.getResourcesPath());
        this.handlers[entityId].addEventListener('changed', this.onHandlerChanged.bind(this));
        this.handlers[entityId].addEventListener('destroyed', this.onHandlerDestroyed.bind(this));
        this.handlers[entityId].addEventListener('log-msg', (ev) => this.logMessage(ev.detail));

        this.sendFunction({
            messageType: 'effect-added',
            entityId: entityId,
            ...this.handlers[entityId].getState()
        });
    }

    createHandlerFromType(entityId, type) {
        switch (type) {
            case 'video': return new VideoHandler(entityId, this.dom);
            case 'image': return new ImageHandler(entityId, this.dom);
            case 'web': return new WebsiteHandler(entityId, this.dom);
            case 'audio': return new AudioHandler(entityId, this.dom);
            default:
                throw new Error(`Unsupported media type ${type}`);
        }
    }

    destroyHandler(entityId) {
        if (entityId in this.handlers) {
            this.handlers[entityId].destroy();
            delete this.handlers[entityId];
        }
    }

    resetAll() {
        for (const entityId in this.handlers) {
            this.destroyHandler(entityId);
        }
    }

    restart() {
        this.dispatchEvent(new CustomEvent('relaunch'));
    }

    onHandlerDestroyed(event) {
        const entityId = event.detail;
        if (entityId in this.handlers) {
            delete this.handlers[entityId];
        }

        this.sendFunction({
            messageType: 'effect-removed',
            entityId: entityId
        });
    }

    onHandlerChanged(event) {
        const entityId = event.detail;
        if (entityId in this.handlers) {
            this.sendFunction({
                messageType: 'effect-changed',
                entityId: entityId,
                ...this.handlers[entityId].getState()
            });
        } else {
            this.reportWarning('Got update events on untracked effect');
        }
    }

    sendMessageToHandler(entityId, msg) {
        if (entityId in this.handlers) {
            if (this.handlers[entityId].handleMessage(msg)) {
                this.sendFunction({
                    messageType: 'effect-changed',
                    entityId: entityId,
                    ...this.handlers[entityId].getState()
                });
            }
        } else {
            this.reportWarning(`Trying to issue command for non-existant entity id ${entityId}`);
        }
    }

    getComponentInfo() {
        return {
            componentId: this.componentId,
            componentName: 'media',
            status: 'online'
        };
    }

    _regularUpdate() {
        if (!this.sendFunction) {
            return;
        }

        const nofStaticKeys = 1; // effectType is always present
        for (const entityId in this.handlers) {
            const state = this.handlers[entityId].getRegularUpdateState();
            if (Object.keys(state).length > nofStaticKeys) {
                this.sendFunction({
                    messageType: 'effect-changed',
                    entityId: entityId,
                    ...state
                });
            }
        }
    }

};
