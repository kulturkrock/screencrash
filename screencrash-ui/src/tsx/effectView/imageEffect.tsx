import * as React from "react";

import style from "../../less/effectView.module.less";
import { IEffect, IEffectActionEvent } from "../types";

import { MdStop, MdOutlineImage, MdOutlineHideImage } from "react-icons/md";

interface IState {
  stopEnabled: boolean;
}

interface IProps {
  effect: IEffect;
  onEffectAction: (event: IEffectActionEvent) => void;
}

class ImageEffect extends React.PureComponent<IProps, IState> {
  constructor(props: IProps) {
    super(props);
    this.state = {
      stopEnabled: false,
    };
  }

  public render(): JSX.Element {
    return (
      <div className={style.imageInfo}>
        <div className={style.imageName}>{this.props.effect.name}</div>
        <div
          className={`${style.imageAction}`}
          onClick={this.sendToggleHidden.bind(this)}
        >
          {this.getHideButton()}
        </div>
        <div
          className={`${style.imageAction} ${style.imageStop} ${
            this.state.stopEnabled ? style.imageStopEnabled : ""
          }`}
          onClick={this.sendStop.bind(this)}
        >
          <MdStop />
        </div>
      </div>
    );
  }

  private getHideButton(): JSX.Element {
    if (this.props.effect.visible) {
      return <MdOutlineImage />;
    } else {
      return <MdOutlineHideImage />;
    }
  }

  private sendToggleHidden(): void {
    const eventType = this.props.effect.visible ? "hide" : "show";
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: eventType,
      media_type: "image",
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
        media_type: "image",
      });
    }
  }

  private setStopEnabled(enabled: boolean): void {
    this.setState({ ...this.state, stopEnabled: enabled });
  }
}

export { ImageEffect };
