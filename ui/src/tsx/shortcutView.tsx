import * as React from "react";
import { INodeCollection } from "types";

import style from "../less/shortcutView.module.less";
import { IShortcut } from "./types";

interface IProps {
  shortcuts: IShortcut[];
  nodes: INodeCollection;
  onTriggerPredefinedActions: (actions: string[]) => void;
  onSendUIMessage: (
    messageType: string,
    params: { [index: string]: unknown },
  ) => void;
}

interface IState {
  selectedNode: string;
}

class ShortcutView extends React.PureComponent<IProps, IState> {
  constructor(props: IProps) {
    super(props);
    const nodeKeys = Object.keys(this.props.nodes);
    this.state = {
      selectedNode: nodeKeys.length > 0 ? nodeKeys[0] : "",
    };
  }

  public render(): JSX.Element {
    return (
      <div className={style.container}>
        <div className={style.nodeSelector}>
          <select
            id="nodeSelector"
            onChange={(e) => this.setState({ selectedNode: e.target.value })}
          >
            {Object.entries(this.props.nodes)
              .sort((a, b) => a[1].lineNumber - b[1].lineNumber)
              .map(([nodeKey]) => (
                <option key={nodeKey} value={nodeKey}>
                  {`${nodeKey}. ${this.props.nodes[nodeKey].prompt.substring(
                    0,
                    25 - nodeKey.length,
                  )}`}
                </option>
              ))}
          </select>
          <button
            onClick={this.gotoNode.bind(this)}
            disabled={this.state.selectedNode === ""}
          >
            Go to node
          </button>
        </div>

        {this.props.shortcuts.map((shortcut, i) => (
          <div key={`shortcut_${i}`} className={style.shortcut}>
            <div className={style.shortcutTitle} title={shortcut.hotkey || ""}>
              {shortcut.title}
            </div>
            <button onClick={this.triggerActions.bind(this, shortcut.actions)}>
              Trigger
            </button>
          </div>
        ))}
      </div>
    );
  }

  private gotoNode() {
    this.props.onSendUIMessage("goto-node", { node: this.state.selectedNode });
  }

  private triggerActions(actions: string[]): void {
    this.props.onTriggerPredefinedActions(actions);
  }
}

export { ShortcutView };
