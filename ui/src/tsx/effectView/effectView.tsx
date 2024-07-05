import * as React from "react";

import { IEffect, IEffectActionEvent, IEmpty } from "../types";
import style from "../../less/effectView.module.less";
import { StatusEffect } from "./statusEffect";

interface IProps {
  effects: IEffect[];
  onEffectAction: (event: IEffectActionEvent) => void;
}

class EffectView extends React.PureComponent<IProps, IEmpty> {
  public render(): JSX.Element {
    return (
      <div className={style.box}>
        {this.props.effects.map((effect) => (
          <StatusEffect
            key={effect.entityId}
            effect={effect}
            onEffectAction={this.props.onEffectAction}
          />
        ))}
      </div>
    );
  }
}

export { EffectView };
