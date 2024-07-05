import * as React from "react";

import style from "../../less/effectView.module.less";
import { IEffect, IEffectActionEvent } from "../types";
import { ProgressBar } from "./progressBar";

import {
  MdPlayArrow,
  MdPause,
  MdStop,
  MdLoop,
  MdVolumeOff,
  MdVolumeUp,
} from "react-icons/md";

interface IState {
  volume: number;
  stopEnabled: boolean;
}

interface IProps {
  effect: IEffect;
  onEffectAction: (event: IEffectActionEvent) => void;
}

class AudioEffect extends React.PureComponent<IProps, IState> {
  constructor(props: IProps) {
    super(props);
    this.state = {
      volume: this.props.effect.volume ? this.props.effect.volume : 50,
      stopEnabled: false,
    };
  }

  public render(): JSX.Element {
    return (
      <div>
        <div className={style.audioInfo}>
          <div className={style.audioName}>{this.props.effect.name}</div>
          <div
            className={`${style.audioAction} ${style.audioMute}`}
            onClick={this.sendToggleMute.bind(this)}
          >
            {this.getMuteButton()}
          </div>
          <div
            className={`${style.audioAction} ${style.audioPlayPause}`}
            onClick={this.sendPlayPause.bind(this)}
          >
            {this.getPlayPauseButton()}
          </div>
          <div
            className={`${style.audioAction} ${style.audioLoop} ${
              this.props.effect.looping ? style.looping : ""
            }`}
            onClick={this.sendToggleLoop.bind(this)}
          >
            <MdLoop />
          </div>
          <div
            className={`${style.audioAction} ${style.audioStop} ${
              this.state.stopEnabled ? style.audioStopEnabled : ""
            }`}
            onClick={this.sendStop.bind(this)}
          >
            <MdStop />
          </div>
          <div className={style.volumeValue}>{this.props.effect.volume}</div>
          <input
            className={`${style.volumeInput} ${style.slider}`}
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

  private updateVolume(volume: number): void {
    this.setState({ ...this.state, volume: volume });
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "change_volume",
      media_type: "audio",
      numericValue: volume,
    });
  }

  private sendToggleMute(): void {
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "toggle_mute",
      media_type: "audio",
    });
  }

  private sendPlayPause(): void {
    const eventType = this.props.effect.playing ? "pause" : "play";
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: eventType,
      media_type: "audio",
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
        media_type: "audio",
      });
    }
  }

  private sendToggleLoop(): void {
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "toggle_loop",
      media_type: "audio",
    });
  }

  private setStopEnabled(enabled: boolean): void {
    this.setState({ ...this.state, stopEnabled: enabled });
  }

  private setTimestamp(time: number): void {
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "seek",
      media_type: "audio",
      numericValue: time,
    });
  }
}

export { AudioEffect };
