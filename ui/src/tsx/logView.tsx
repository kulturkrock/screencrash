import * as React from "react";
import { ILogMessage, IEmpty } from "./types";

import style from "../less/logView.module.less";

import { MdInfo, MdWarning, MdError } from "react-icons/md";

interface IProps {
  logMessages: ILogMessage[];
  onClearMessages: () => void;
}

class LogView extends React.PureComponent<IProps, IEmpty> {
  constructor(props: IProps) {
    super(props);
  }

  public render(): JSX.Element {
    return (
      <div>
        <div className={style.clearLogMessagesButton}>
          <button onClick={this.clearLogMessages.bind(this)}>
            Clear log messages
          </button>
        </div>
        {this.props.logMessages
          .slice()
          .reverse()
          .map((msg) => (
            <div
              className={style.logMessage}
              key={`${msg.origin}_${msg.timestamp}`}
            >
              <div className={style.logMessageLeft}>
                <LogMessageIcon level={msg.level} />
                <div className={style.logMessageOrigin}>{msg.origin}</div>
              </div>
              <div className={style.logMessageRight}>
                <div>{msg.message}</div>
                <div className={style.logMessageTime}>
                  {new Date(msg.timestamp * 1000).toLocaleString()}
                </div>
              </div>
            </div>
          ))}
      </div>
    );
  }

  private clearLogMessages(): void {
    if (this.props.onClearMessages) {
      this.props.onClearMessages();
    }
  }
}

function LogMessageIcon(props: { level: string }): JSX.Element {
  if (props.level === "info") {
    return <MdInfo className={style.logMessageIcon} />;
  } else if (props.level === "warning") {
    return <MdWarning className={style.logMessageIcon} />;
  } else if (props.level === "error") {
    return <MdError className={style.logMessageIcon} />;
  } else {
    // Unknown type - no icon
    return <div></div>;
  }
}

export { LogView };
