
const VisualHandler = require('./visualhandler');
const path = require('path');
const fs = require('fs');
const $ = require('jquery');

class SeamlessVideo extends EventTarget {

    constructor(mimeCodec) {
        super();
        this.mimeCodec = mimeCodec;
        this.videoNode = null; // Public, but can only be used after init()
        this.mediaSource = null;
        this.looping = false;
        this.currentFilePath = null;
        this.changedFilePath = false;
        this.playedFilesDuration = 0;
    }

    init(uiWrapper, id, audioDisabled, autostart, filePath) {
        uiWrapper.innerHTML = `
            <video id = "video-${id}" class = "video-media" ${audioDisabled ? 'muted' : ''} ${autostart ? 'autoplay' : ''}>
            </video>
        `;
        this.videoNode = uiWrapper.getElementsByTagName('video')[0];
        this.mediaSource = new MediaSource();
        this.videoNode.src = URL.createObjectURL(this.mediaSource);
        this.videoNode.onended = this._onEnded.bind(this);

        this.currentFilePath = filePath;

        this.mediaSource.addEventListener('sourceopen', async() => {
            const sourceBuffer = this.mediaSource.addSourceBuffer(this.mimeCodec);
            sourceBuffer.mode = 'sequence';
            this._addFileToEnd(filePath);
        });

        this.checkEndInterval = setInterval(() => this._checkEnd(), 50);
    }

    setLooping(looping) {
        this.looping = looping;
    }

    nextFile(filePath) {
        this.currentFilePath = filePath;
        this.changedFilePath = true;
    }

    playedFilesTime() {
        return this.playedFilesDuration;
    };

    destroy() {
        clearInterval(this.checkEndInterval);
    }

    _addFileToEnd(filePath, callback) {
        if (!Number.isNaN(this.mediaSource.duration)) {
            this.playedFilesDuration = this.mediaSource.duration;
        }
        const videoData = fs.readFileSync(filePath);
        const sourceBuffer = this.mediaSource.sourceBuffers[0];
        sourceBuffer.appendBuffer(Buffer.from(videoData));
        sourceBuffer.addEventListener('updateend', () => {
            if (callback) {
                callback();
            }
        }, { once: true });
    }

    _checkEnd() {
        if (this.mediaSource.readyState === 'open' &&
            this.mediaSource.sourceBuffers[0] &&
            !this.mediaSource.sourceBuffers[0].updating &&
            (this.videoNode.duration - this.videoNode.currentTime < 0.5)
        ) {
            if (this.changedFilePath) {
                this._addFileToEnd(this.currentFilePath, () => this.dispatchEvent(new CustomEvent('new-file')));
                this.changedFilePath = false;
            } else if (this.looping) {
                this._addFileToEnd(this.currentFilePath, () => this.dispatchEvent(new CustomEvent('looped')));
            } else {
                this.mediaSource.endOfStream();
            }
        }
    }

    _onEnded() {
        this.dispatchEvent(
            new CustomEvent('ended')
        );
    }

}

class ConvenientVideo extends EventTarget {

    constructor() {
        super();
        this.videoNode = null; // Public, but can only be used after attach()
        this.looping = false;
        this.currentFilePath = null;
        this.changedFilePath = false;
    }

    init(uiWrapper, id, audioDisabled, autostart, filePath) {
        uiWrapper.innerHTML = `
        <video id = "video-${id}" class = "video-media" ${audioDisabled ? 'muted' : ''} ${autostart ? 'autoplay' : ''}>
            <source src="${filePath}" type="video/mp4" />
        </video>
        `;
        this.videoNode = uiWrapper.getElementsByTagName('video')[0];
        this.videoNode.onended = this._onEnded.bind(this);
    }

    setLooping(looping) {
        this.looping = looping;
    }

    nextFile(filePath) {
        this.currentFilePath = filePath;
        this.changedFilePath = true;
    }

    playedFilesTime() {
        return 0;
    }

    destroy() {}

    _onEnded() {
        if (this.changedFilePath) {
            this.videoNode.children[0].setAttribute('src', this.currentFilePath);
            this.videoNode.load();
            this.videoNode.play();
            this.changedFilePath = false;
            this.dispatchEvent(
                new CustomEvent('new-file')
            );
        } else if (this.looping) {
            this.videoNode.play();
            this.dispatchEvent(
                new CustomEvent('looped')
            );
        } else {
            this.dispatchEvent(
                new CustomEvent('ended')
            );
        }
    }

}

module.exports = class VideoHandler extends VisualHandler {

    constructor(id, dom) {
        super(id, dom);
        this.audioDisabled = (process.env.SCREENCRASH_NO_AUDIO === 'true');
        this.visualDisabled = (process.env.SCREENCRASH_NO_WINDOW === 'true');
    }

    init(createMessage, resourcesPath) {
        super.init(createMessage, resourcesPath);
        this.resourcesPath = resourcesPath;

        const filePath = `${this.resourcesPath}/${createMessage.asset}`;

        const autostart = createMessage.autostart === undefined || createMessage.autostart;
        if (createMessage.seamless) {
            this.video = new SeamlessVideo(createMessage.mimeCodec);
        } else {
            this.video = new ConvenientVideo();
        }
        this.video.init(this.uiWrapper, this.id, this.audioDisabled, autostart, filePath);
        this.video.addEventListener('new-file', this.onNewFile.bind(this));
        this.video.addEventListener('looped', this.onLooped.bind(this));
        this.video.addEventListener('ended', this.onEnded.bind(this));

        // Set up events and basic data
        const videoNode = this.video.videoNode;

        videoNode.addEventListener('error', this.onError.bind(this), true);
        videoNode.onloadeddata = this.onLoadedData.bind(this);
        videoNode.ontimeupdate = this.onTimeUpdated.bind(this);
        videoNode.onvolumechange = this.onVolumeChanged.bind(this);
        this.nofLoops = (createMessage.looping !== undefined ? createMessage.looping : 1) - 1;
        if (this.nofLoops !== 0) {
            this.video.setLooping(true);
        }
        this.lastRecordedTime = -1;

        // Variables to keep track of fade out on end
        this.finalFadeOutTime = createMessage.fadeOut || 0;
        this.finalFadeOutStarted = false;
        this.fadeStartVolume = 0;

        this.destroyOnEnd = createMessage.destroyOnEnd ?? true;

        // Set name of this handler
        this.name = path.parse(createMessage.asset).name;
        if (createMessage.displayName) {
            this.name = createMessage.displayName; // Override name
        }
    }

    destroy() {
        super.destroy();
        this.video.destroy();
    }

    getRegularUpdateState() {
        const data = {
            ...super.getRegularUpdateState(),
            effectType: 'video'
        };
        if (!this.visualDisabled) {
            data.currentImage = this.getScreenshot();
        }
        return data;
    }

    getState() {
        const data = {
            ...super.getState(),
            effectType: 'video',
            name: this.name,
            duration: this.getDuration(),
            currentTime: this.getCurrentTime(),
            lastSync: Date.now(),
            playing: this.isPlaying(),
            looping: this.isLooping()
        };
        if (!this.audioDisabled) {
            data.muted = this.isMuted();
            data.volume = this.getVolume();
        }
        if (!this.visualDisabled) {
            data.currentImage = this.getScreenshot();
        }
        return data;
    }

    handleMessage(msg) {
        switch (msg.command) {
            case 'play':
                this.play();
                break;
            case 'pause':
                this.pause();
                break;
            case 'seek':
                this.seek(msg.position);
                break;
            case 'set_volume':
                // Fades manually change volume. Avoid that.
                this.stopFade();
                this.setVolume(msg.volume);
                break;
            case 'toggle_mute':
                // Fades manually change volume. Avoid that.
                this.stopFade();
                this.setMuted(!this.isMuted());
                break;
            case 'set_loops':
                this.nofLoops = msg.looping - 1;
                this.video.setLooping(this.nofLoops !== 0);
                break;
            case 'set_next_file':
                this.video.nextFile(`${this.resourcesPath}/${msg.asset}`);
                break;
            default:
                return super.handleMessage(msg);
        }

        // If not handled we have already returned false
        return true;
    }

    isPlaying() {
        const videoNode = this.video.videoNode;
        return videoNode &&
            !videoNode.paused &&
            !videoNode.ended &&
            videoNode.readyState > 2;
    }

    isLooping() {
        return this.nofLoops !== 0;
    }

    getDuration() {
        return this.video.videoNode ? this.video.videoNode.duration - this.video.playedFilesTime() : 0;
    }

    getCurrentTime() {
        return this.video.videoNode ? Math.max(this.video.videoNode.currentTime - this.video.playedFilesTime(), 0) : 0;
    }

    isMuted() {
        return this.video.videoNode ? this.video.videoNode.muted : false;
    }

    getVolume() {
        return this.video.videoNode ? Math.round(this.video.videoNode.volume * 100) : 0;
    }

    getScreenshot() {
        const canvas = document.createElement('canvas');
        canvas.width = this.video.videoNode.clientWidth;
        canvas.height = this.video.videoNode.clientHeight;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(this.video.videoNode, 0, 0, canvas.width, canvas.height);

        const result = canvas.toDataURL('image/jpeg', 0.1);
        return result;
    }

    play() {
        if (this.video.videoNode) {
            this.video.videoNode.play();
        }
    }

    pause() {
        if (this.video.videoNode) {
            this.video.videoNode.pause();
        }
    }

    seek(position) {
        if (this.video.videoNode && position !== undefined && position !== null) {
            this.video.videoNode.currentTime = position + this.video.playedFilesTime();
            this.stopFade(this.finalFadeOutStarted);
            this.finalFadeOutStarted = false;
        }
    }

    setMuted(muted) {
        if (this.video.videoNode && !this.audioDisabled) {
            this.video.videoNode.muted = muted;
        }
    }

    setVolume(volume) {
        if (this.video.videoNode && !this.audioDisabled) {
            this.video.videoNode.volume = volume / 100;
        }
    }

    setupFade(fadeTime, from, to, onFadeDone) {
        if (this.audioDisabled) {
            super.setupFade(fadeTime, from, to, onFadeDone);
        } else {
            super.setupFade(fadeTime, from, to, () => {});
            const startVolume = (from == null ? this.getVolume() : from * 100);
            this.fadeStartVolume = startVolume;
            this.setVolume(startVolume);
            $(this.video.videoNode).animate({ volume: to }, fadeTime, onFadeDone);
        }
    }

    stopFade(requireReset) {
        super.stopFade(requireReset);
        $(this.video.videoNode).stop(true, true);
        if (requireReset && !this.audioDisabled) {
            this.setVolume(this.fadeStartVolume);
        }
    }

    onLooped() {
        this.nofLoops -= 1;
        if (this.nofLoops === 0) {
            this.video.setLooping(false);
        }
    }

    onNewFile() {
        this.emitEvent('changed', this.id);
    }

    onError() {
        this.emitError(`Unable to play video with id ${this.id}`);
        this.destroy();
    }

    onEnded() {
        if (this.destroyOnEnd) {
            this.destroy();
        }
    }

    onLoadedData() {
        this.emitEvent('changed', this.id);
    }

    onVolumeChanged() {
        this.emitEvent('changed', this.id);
    }

    onTimeUpdated(event) {
        if (this.finalFadeOutTime > 0 && !this.finalFadeOutStarted) {
            const timeLeft = (this.getDuration() - this.getCurrentTime()) + (this.nofLoops * this.getDuration());
            if (timeLeft < this.finalFadeOutTime) {
                this.finalFadeOutStarted = true;
                this.startFade(this.finalFadeOutTime, null, 0.0, true);
            }
        }

        const currentTime = this.video.videoNode.currentTime;
        if (currentTime < this.lastRecordedTime && currentTime > 0) {
            // Time has changed backwards. Either we looped over and
            // started over or we time jumped. In both cases, we probably
            // want to notify the world about this change.
            this.emitEvent('changed', this.id);
        }
        this.lastRecordedTime = currentTime;
    }

};
