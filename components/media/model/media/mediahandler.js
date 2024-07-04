
module.exports = class MediaHandler extends EventTarget {

    constructor(id, dom) {
        super();
        this.id = id;
        this.isDestroyed = false;
        this.uiWrapper = this._createMediaWrapper(dom);
    }

    _createMediaWrapper(dom) {
        const element = dom.createElement('div');
        element.id = 'wrapper-' + this.id;
        element.className = 'media-wrapper hidden';
        dom.body.appendChild(element);
        return element;
    }

    emitEvent(eventType, data) {
        if (!this.isDestroyed) {
            this.dispatchEvent(
                new CustomEvent(eventType, { detail: data })
            );
        }
    }

    emitWarning(msg) {
        this.emitEvent('log-msg', { level: 'warning', message: msg });
    }

    emitError(msg) {
        this.emitEvent('log-msg', { level: 'error', message: msg });
    }

    init(msg, resourcesPath) {
        // Override this method to set initial state from
        // creation message

        if (msg.fadeIn) {
            this.startFade(msg.fadeIn.time, msg.fadeIn.from, msg.fadeIn.to, false);
        }
    }

    getRegularUpdateState() {
        // Override to add regular state data
        return {
            effectType: 'unknown'
        };
    }

    getState() {
        // Override to add state data
        return {
            effectType: 'unknown'
        };
    }

    handleMessage(msg) {
        // Override this to handle commands
        switch (msg.command) {
            case 'fade':
                this.startFade(msg.time, null, msg.target, msg.stopOnDone);
                break;
            default:
                this.emitWarning(`Unhandled command ${msg.command}`);
                return false;
        }

        return true;
    }

    startFade(time, from, to, stopOnDone) {
        const fadeTime = parseFloat(time) * 1000;
        const onFadeDone = (stopOnDone ? this.destroy.bind(this) : null);
        this.setupFade(fadeTime, from, to, onFadeDone);
    }

    // ---- Implemented by children who needs fading ----- //
    setupFade(fadeTime, from, to, onFadeDone) {}

    stopFade(requireReset) {}
    // ---------------- End of fade functions ------------- //

    destroy() {
        if (!this.isDestroyed) {
            this.uiWrapper.parentNode.removeChild(this.uiWrapper);
            this.emitEvent('destroyed', this.id);
            this.isDestroyed = true;
        }
    }

};
