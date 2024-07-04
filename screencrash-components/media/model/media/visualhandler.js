
const MediaHandler = require('./mediahandler');
const $ = require('jquery');

const { addClass, removeClass, hasClass } = require('../domutils');
const AVAILABLE_ANIMATIONS = ['shake', 'nod', 'spin'];

module.exports = class VisualHandler extends MediaHandler {

    constructor(id, dom) {
        super(id, dom);
        this.fadeStartOpacity = 0;
    }

    init(msg, resourcesPath) {
        super.init(msg, resourcesPath);

        if (msg.transitions) {
            const cssTransitions = [];
            // Movement along X-axis
            const transitionMoveX = this._createCssTransition([msg.transitions.move_x, msg.transitions.move], 'left');
            if (transitionMoveX) cssTransitions.push(transitionMoveX);
            // Movement along Y-axis
            const transitionMoveY = this._createCssTransition([msg.transitions.move_y, msg.transitions.move], 'top');
            if (transitionMoveY) cssTransitions.push(transitionMoveY);
            // Width
            const transitionWidth = this._createCssTransition([msg.transitions.width, msg.transitions.size], 'width');
            if (transitionWidth) cssTransitions.push(transitionWidth);
            // Height
            const transitionHeight = this._createCssTransition([msg.transitions.height, msg.transitions.size], 'height');
            if (transitionHeight) cssTransitions.push(transitionHeight);
            // Opacity
            const transitionOpacity = this._createCssTransition([msg.transitions.opacity], 'opacity');
            if (transitionOpacity) cssTransitions.push(transitionOpacity);

            const fullCss = cssTransitions.join(', ');
            if (fullCss) {
                this.uiWrapper.style.transition = fullCss;
            }
        }

        if (msg.animation && AVAILABLE_ANIMATIONS.includes(msg.animation)) {
            this.uiWrapper.className += ` animation-${msg.animation}`;
        }

        this.setViewport(msg.x, msg.y, msg.width, msg.height, msg.usePercentage);

        if (msg.visible) {
            this.setVisible(true);
        }

        if (msg.opacity != null) {
            this.setOpacity(msg.opacity);
        }

        if (typeof msg.layer === 'number') {
            this.setLayer(msg.layer);
        }
    }

    _createCssTransition(configs, property) {
        const duration = configs.reduceRight((prev, curr) => curr && curr.duration != null ? curr.duration : prev, null);
        const type = configs.reduceRight((prev, curr) => curr && curr.type != null ? curr.type : prev, null);
        const delay = configs.reduceRight((prev, curr) => curr && curr.delay != null ? curr.delay : prev, null);
        if (duration || type || delay) {
            return `${property} ${duration || 1}s ${type || 'ease'} ${delay || 0}s`;
        }
        return '';
    }

    getRegularUpdateState() {
        const parentRegularState = super.getRegularUpdateState();
        return {
            ...parentRegularState,
            effectType: 'unknown'
        };
    }

    getState() {
        const parentState = super.getState();
        return {
            ...parentState,
            effectType: 'unknown',
            visible: this.isVisible(),
            opacity: this.getOpacity(),
            viewport_x: this.getX(),
            viewport_y: this.getY(),
            viewport_width: this.getWidth(),
            viewport_height: this.getHeight(),
            layer: this.getLayer()
        };
    }

    handleMessage(msg) {
        switch (msg.command) {
            /* Add commands for all media types here */
            case 'show':
                this.setVisible(true);
                break;
            case 'hide':
                this.setVisible(false);
                break;
            case 'opacity':
                // Fades manually change opacity. Avoid that.
                this.stopFade();
                this.setOpacity(msg.opacity);
                break;
            case 'viewport':
                this.setViewport(msg.x, msg.y, msg.width, msg.height, msg.usePercentage);
                break;
            case 'layer':
                this.setLayer(msg.layer);
                break;
            default:
                return super.handleMessage(msg);
        }

        // If not handled we have already returned false
        return true;
    }

    isVisible() {
        return this.uiWrapper && !hasClass(this.uiWrapper, 'hidden');
    }

    setVisible(visible) {
        if (this.uiWrapper) {
            if (visible) {
                removeClass(this.uiWrapper, 'hidden');
            } else {
                addClass(this.uiWrapper, 'hidden');
            }
        }
    }

    getOpacity() {
        if (this.uiWrapper.style.opacity === '') {
            return 1.0;
        }
        return parseFloat(this.uiWrapper.style.opacity);
    }

    setOpacity(opacity) {
        if (opacity >= 0.0 && opacity <= 1.0) {
            this.uiWrapper.style.opacity = opacity;
        }
    }

    getX() {
        return this.uiWrapper.style.left;
    }

    getY() {
        return this.uiWrapper.style.top;
    }

    getWidth() {
        return this.uiWrapper.clientWidth;
    }

    getHeight() {
        return this.uiWrapper.clientHeight;
    }

    setViewport(x, y, width, height, percentage = false) {
        const suffix = (percentage ? '%' : 'px');

        if (x !== undefined) {
            this.uiWrapper.style.left = x + suffix;
        }
        if (y !== undefined) {
            this.uiWrapper.style.top = y + suffix;
        }
        if (width !== undefined) {
            this.uiWrapper.style.width = width + suffix;
        }
        if (height !== undefined) {
            this.uiWrapper.style.height = height + suffix;
        }
    }

    getLayer() {
        return this.uiWrapper.style.zIndex;
    }

    setLayer(layer) {
        this.uiWrapper.style.zIndex = layer;
    }

    setupFade(fadeTime, from, to, onFadeDone) {
        super.setupFade(fadeTime, from, to, () => {});
        this.fadeStartOpacity = (from == null ? this.getOpacity() : from);
        this.setOpacity(this.fadeStartOpacity);
        $(this.uiWrapper).animate({ opacity: to }, fadeTime, onFadeDone);
    }

    stopFade(requireReset) {
        super.stopFade(requireReset);
        $(this.uiWrapper).stop(true, true);
        if (requireReset) {
            this.setOpacity(this.fadeStartOpacity);
        }
    }

};
