import * as React from "react";

import style from "../../less/effectView.module.less";
import { IEffect, IEffectActionEvent } from "../types";

import {
  MdStop,
  MdRefresh,
  MdOutlineImage,
  MdOutlineHideImage,
} from "react-icons/md";

interface IState {
  stopEnabled: boolean;
}

interface IProps {
  effect: IEffect;
  onEffectAction: (event: IEffectActionEvent) => void;
}

class WebEffect extends React.PureComponent<IProps, IState> {
  constructor(props: IProps) {
    super(props);
    this.state = {
      stopEnabled: false,
    };
  }

  public render(): JSX.Element {
    return (
      <div className={style.webInfo}>
        <div className={style.webAddress}>{this.props.effect.name}</div>
        <div
          className={`${style.webAction}`}
          onClick={this.sendToggleHidden.bind(this)}
        >
          {this.getHideButton()}
        </div>
        <div
          className={`${style.webAction}`}
          onClick={this.sendRefreshPage.bind(this)}
        >
          <MdRefresh />
        </div>
        <div
          className={`${style.webAction} ${style.webStop} ${
            this.state.stopEnabled ? style.webStopEnabled : ""
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
      media_type: "web",
    });
  }

  private sendRefreshPage(): void {
    this.props.onEffectAction({
      entityId: this.props.effect.entityId,
      action_type: "refresh",
      media_type: "web",
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

export { WebEffect };
