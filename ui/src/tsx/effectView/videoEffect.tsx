import * as React from "react";

import style from "../../less/effectView.module.less";
import { EffectType, IEffect, IEffectActionEvent } from "../types";
import { ProgressBar } from "./progressBar";

import {
  MdPlayArrow,
  MdPause,
  MdStop,
  MdLoop,
  MdVolumeOff,
  MdVolumeUp,
  MdOutlineImage,
  MdOutlineHideImage,
} from "react-icons/md";

interface IState {
  volume: number;
  stopEnabled: boolean;
}

interface IProps {
  effect: IEffect;
  onEffectAction: (event: IEffectActionEvent) => void;
}

class VideoEffect extends React.PureComponent<IProps, IState> {
  constructor(props: IProps) {
    super(props);
    this.state = {
      volume: this.props.effect.volume ? this.props.effect.volume : 50,
      stopEnabled: false,
    };
  }

  public render(): JSX.Element {
    return (
      <div className={style.videoContainer}>
        <img
          src={this.props.effect.currentImage}
          className={style.videoImage}
        />
        <div className={style.videoInfo}>
          <div className={style.videoName}>{this.props.effect.name}</div>
          <div
            className={`${style.videoAction} ${style.videoMute} ${style.temporarilyDisabled}`}
            onClick={this.sendToggleMute.bind(this)}
          >
            {this.getMuteButton()}
          </div>
          <div
            className={`${style.videoAction} ${style.videoPlayPause}`}
            onClick={this.sendPlayPause.bind(this)}
          >
            {this.getPlayPauseButton()}
          </div>
          <div
            className={`${style.videoAction} ${style.videoHide}`}
            onClick={this.sendToggleHidden.bind(this)}
          >
            {this.getHideButton()}
          </div>
          <div
            className={`${style.videoAction} ${style.videoLoop} ${
              this.props.effect.looping ? style.looping : ""
            }`}
            onClick={this.sendToggleLoop.bind(this)}
          >
            <MdLoop />
          </div>
          <div
            className={`${style.videoAction} ${style.videoStop} ${
              this.state.stopEnabled ? style.videoStopEnabled : ""
            }`}
            onClick={this.sendStop.bind(this)}
          >
            <MdStop />
          </div>
          <div className={`${style.volumeValue} ${style.temporarilyRemoved}`}>
            {this.props.effect.volume}
          </div>
          <input
            className={`${style.volumeInput} ${style.slider} ${style.temporarilyRemoved}`}
            type="range"
            min="0"
            max="100"
            value={this.props.effect.volume}
            onChange={(e) => this.updateVolume(parseInt(e.target.value))}
          />
        </div>
        <ProgressBar
          duration={this.props.effect.duration}
          currentTime={this.props.effect.currentTime}
          lastUpdated={this.props.effect.lastSync}
          looping={this.props.effect.looping}
          running={this.props.effect.playing}
          onClicked={this.setTimestamp.bind(this)}
        />
      </div>
    );
  }

  private getMuteButton(): JSX.Element {
    if (this.props.effect.muted) {
      return <MdVolumeOff />;
    } else {
      return <MdVolumeUp />;
    }
  }

  private getPlayPauseButton(): JSX.Element {
    if (this.props.effect.playing) {
      return <MdPause />;
    } else {
      return <MdPlayArrow />;
    }
  }

  private getHideButton(): JSX.Element {
    if (this.props.effect.visible) {
      return <MdOutlineImage />;
    } else {
      return <MdOutlineHideImage />;
    }
  }

  private effectTypeAsString(): string {
    switch (this.props.effect.type) {
      case EffectType.Video:
        return "video";
      case EffectType.Image:
        return "image";
      case EffectType.WebPage:
        return "web";
      default:
        return "unknown";
    }
  }

  private updateVolume(volume: number): void {
    this.setState({ ...this.state, volume: volume });
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "change_volume",
      media_type: this.effectTypeAsString(),
      numericValue: volume,
    });
  }

  private sendToggleHidden(): void {
    const eventType = this.props.effect.visible ? "hide" : "show";
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: eventType,
      media_type: this.effectTypeAsString(),
    });
  }

  private sendToggleMute(): void {
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "toggle_mute",
      media_type: this.effectTypeAsString(),
    });
  }

  private sendPlayPause(): void {
    const eventType = this.props.effect.playing ? "pause" : "play";
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: eventType,
      media_type: this.effectTypeAsString(),
    });
  }

  private sendStop(): void {
    if (!this.state.stopEnabled) {
      this.setStopEnabled(true);
      setTimeout(this.setStopEnabled.bind(this, false), 2000);
    } else {
      this.props.onEffectAction({
        entityId: this.props.effect.entityId,
        action_type: "destroy",
        media_type: this.effectTypeAsString(),
      });
    }
  }

  private sendToggleLoop(): void {
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "toggle_loop",
      media_type: this.effectTypeAsString(),
    });
  }

  private setStopEnabled(enabled: boolean): void {
    this.setState({ ...this.state, stopEnabled: enabled });
  }

  private setTimestamp(time: number): void {
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "seek",
      media_type: this.effectTypeAsString(),
      numericValue: time,
    });
  }
}

export { VideoEffect };
