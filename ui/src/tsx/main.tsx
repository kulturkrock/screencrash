import { PureComponent, StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { RealCoreConnection, ICoreConnection } from "./coreConnection";
import { LiveScreen } from "./liveScreen";
import { IEmpty } from "./types";
import style from "../less/main.module.less";

interface IState {
  coreAddress: string;
  coreConnection: ICoreConnection;
  isConnected: boolean;
}

class Main extends PureComponent<IEmpty, IState> {
  constructor(props: IEmpty) {
    super(props);
    const queryParams = new URLSearchParams(window.location.search);
    const coreAddress = queryParams.get("core");
    this.state = {
      coreAddress,
      coreConnection: new RealCoreConnection(coreAddress),
      isConnected: false,
    };

    this.state.coreConnection.addEventListener("connection", (event) => {
      this.setState({ isConnected: event.detail.connected });
    });
  }

  public render() {
    const queryParams = new URLSearchParams(window.location.search);
    const allowCommands = queryParams.get("mode") !== "safe";
    const showStatusContainer = queryParams.get("nostatus") === null;
    return (
      <div className={style.gridContainer}>
        <div className={style.header}>
          <div>Mode: Live {allowCommands ? "" : "[SAFE MODE]"}</div>
          <div>{this.state.isConnected ? "CONNECTED" : "CONNECTING..."}</div>
          <div>
            <form>
              <label>Core: </label>
              <input
                className={style.addressInput}
                autoComplete="off"
                type="text"
                name="core"
                defaultValue={this.state.coreAddress}
              />
            </form>
          </div>
        </div>
        <div className={style.screen}>
          <LiveScreen
            coreConnection={this.state.coreConnection}
            maxNofLogs={100}
            allowCommands={allowCommands}
            showStatusContainer={showStatusContainer}
          />
        </div>
      </div>
    );
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Main />
  </StrictMode>
);
