import {
  ComponentResetMessage,
  ComponentRestartMessage,
  OnTheFlyAction,
  PredefinedActionsTrigger,
} from "./coreMessages";
import {
  INodeCollection,
  IEffect,
  IEffectActionEvent,
  IComponentState,
  IConnectionState,
  ILogMessage,
  IUIConfig,
} from "./types";

const eventNames = {
  nodes: "nodes",
  history: "history",
  script: "script",
  effects: "effects",
  logs: "logs",
  logAdded: "log-added",
  components: "components",
  connection: "connection",
  uiconfig: "uiconfig",
};

/**
 * This class handles the communication with the core.
 * The user calls methods directly to
 * send a message to the core, and can register for events.
 */
interface ICoreConnection extends EventTarget {
  // UI-initiated actions
  handshake(): void;
  prevNode(): void;
  nextNode(runActions: boolean): void;
  sendUICommand(
    messageType: string,
    params: { [index: string]: unknown },
  ): void;
  runActions(): void;
  choosePath(choiceIndex: number, runActions: boolean): void;
  runOnTheFlyAction(action: OnTheFlyAction): void;
  runPredefinedActions(actions: string[]): void;
  handleEffectAction(event: IEffectActionEvent): void;
  handleClearLogMessages(): void;
  handleComponentReset(componentId: string): void;
  handleComponentRestart(componentId: string): void;

  // Events
  addEventListener(
    event: "connection",
    listener: (event: CustomEvent<IConnectionState>) => void,
  ): void;
  addEventListener(
    event: "nodes",
    listener: (event: CustomEvent<INodeCollection>) => void,
  ): void;
  addEventListener(
    event: "uiconfig",
    listener: (event: CustomEvent<IUIConfig>) => void,
  ): void;
  addEventListener(
    event: "history",
    listener: (event: CustomEvent<string[]>) => void,
  ): void;
  addEventListener(
    event: "script",
    listener: (event: CustomEvent<string>) => void,
  ): void;
  addEventListener(
    event: "components",
    listener: (event: CustomEvent<IComponentState[]>) => void,
  ): void;
  addEventListener(
    event: "effects",
    listener: (event: CustomEvent<IEffect[]>) => void,
  ): void;
  addEventListener(
    event: "logs",
    listener: (event: CustomEvent<ILogMessage[]>) => void,
  ): void;
  addEventListener(
    event: "log-added",
    listener: (event: CustomEvent<ILogMessage>) => void,
  ): void;
}

/**
 * This class encapsulates the connection to Core
 */
class RealCoreConnection extends EventTarget implements ICoreConnection {
  private address: string;
  private socket: WebSocket;

  constructor(address: string) {
    super();
    this.address = address;
    this.runOnTheFlyAction = this.runOnTheFlyAction.bind(this);
    this.runPredefinedActions = this.runPredefinedActions.bind(this);
    this.sendUICommand = this.sendUICommand.bind(this);
  }

  private emitConnected(isConnected: boolean) {
    this.dispatchEvent(
      new CustomEvent(eventNames.connection, {
        detail: {
          connected: isConnected,
        },
      }),
    );
  }

  public handshake(): void {
    this.socket = new WebSocket(`ws://${this.address}`);
    this.socket.addEventListener("open", () => {
      console.log(`Got connection to core`);
      this.emitConnected(true);
      this.socket.send(JSON.stringify({ client: "ui" }));
    });
    this.socket.addEventListener("message", (event: MessageEvent) => {
      const { messageType, data } = JSON.parse(event.data);
      switch (messageType) {
        case "history":
          this.dispatchEvent(
            new CustomEvent(eventNames.history, {
              detail: data,
            }),
          );
          break;
        case "nodes":
          this.dispatchEvent(
            new CustomEvent(eventNames.nodes, {
              detail: data,
            }),
          );
          break;
        case "uiconfig":
          this.dispatchEvent(
            new CustomEvent(eventNames.uiconfig, {
              detail: data,
            }),
          );
        case "script":
          this.dispatchEvent(
            new CustomEvent(eventNames.script, { detail: data }),
          );
          break;
        case "components":
          this.dispatchEvent(
            new CustomEvent(eventNames.components, { detail: data }),
          );
          break;
        case "effects":
          this.dispatchEvent(
            new CustomEvent(eventNames.effects, { detail: data }),
          );
          break;
        case "logs":
          this.dispatchEvent(
            new CustomEvent(eventNames.logs, { detail: data }),
          );
          break;
        case "log-added":
          this.dispatchEvent(
            new CustomEvent(eventNames.logAdded, { detail: data }),
          );
          break;
        default:
          console.error(`Unknown message from Core: ${messageType}`);
      }
    });
    this.socket.addEventListener("close", () => {
      console.log(`Lost connection with server. Reconnecting in 1s...`);
      this.emitConnected(false);
      setTimeout(this.handshake.bind(this), 1000);
    });
    this.socket.addEventListener("error", () => {
      console.log(`Got error from websocket connection. Closing connection...`);
      this.socket.close();
    });
  }

  public prevNode(): void {
    this.socket.send(JSON.stringify({ messageType: "prev-node" }));
  }

  public nextNode(runActions: boolean): void {
    this.socket.send(JSON.stringify({ messageType: "next-node", runActions }));
  }

  public sendUICommand(
    messageType: string,
    params: { [index: string]: unknown },
  ): void {
    this.socket.send(JSON.stringify({ messageType, ...params }));
  }

  public runActions(): void {
    this.socket.send(JSON.stringify({ messageType: "run-actions" }));
  }

  public choosePath(choiceIndex: number, runActions: boolean): void {
    this.socket.send(
      JSON.stringify({ messageType: "choose-path", choiceIndex, runActions }),
    );
  }

  public handleEffectAction(event: IEffectActionEvent): void {
    const message: OnTheFlyAction = {
      messageType: "component-action",
      target_component: event.media_type,
      cmd: "",
      assets: [],
      params: {},
    };

    switch (event.action_type) {
      case "play":
        message.cmd = "play";
        message.params["entityId"] = event.entityId;
        break;
      case "pause":
        message.cmd = "pause";
        message.params["entityId"] = event.entityId;
        break;
      case "stop":
        message.cmd = "stop";
        message.params["entityId"] = event.entityId;
        break;
      case "toggle_loop":
        console.log("TODO: Toggle loop");
        break;
      case "toggle_mute":
        message.cmd = "toggle_mute";
        message.params["entityId"] = event.entityId;
        break;
      case "change_volume":
        message.cmd = "set_volume";
        message.params["entityId"] = event.entityId;
        message.params["volume"] = event.numericValue;
        break;
      case "destroy":
        message.cmd = "destroy";
        message.params["entityId"] = event.entityId;
        break;
      case "hide":
        message.cmd = "hide";
        message.params["entityId"] = event.entityId;
        break;
      case "show":
        message.cmd = "show";
        message.params["entityId"] = event.entityId;
        break;
      case "refresh":
        message.cmd = "refresh";
        message.params["entityId"] = event.entityId;
        break;
      case "seek":
        message.cmd = "seek";
        message.params["entityId"] = event.entityId;
        message.params["position"] = event.numericValue;
        break;
      default:
        console.log(`Unhandled effect action event: ${event.action_type}`);
        break;
    }

    this.runOnTheFlyAction(message);
  }

  public runOnTheFlyAction(action: OnTheFlyAction): void {
    action.messageType = "component-action";
    if (action.cmd !== "" && action.cmd !== null) {
      this.socket.send(JSON.stringify(action));
    }
  }

  public runPredefinedActions(actions: string[]): void {
    const msg: PredefinedActionsTrigger = {
      messageType: "run-actions-by-id",
      actions: actions,
    };
    this.socket.send(JSON.stringify(msg));
  }

  public handleClearLogMessages(): void {
    this.socket.send(
      JSON.stringify({
        messageType: "clear-logs",
      }),
    );
  }

  public handleComponentReset(componentId: string): void {
    const message: ComponentResetMessage = {
      messageType: "component-reset",
      componentId: componentId,
    };
    this.socket.send(JSON.stringify(message));
  }

  public handleComponentRestart(componentId: string): void {
    const message: ComponentRestartMessage = {
      messageType: "component-restart",
      componentId: componentId,
    };
    this.socket.send(JSON.stringify(message));
  }
}

export { ICoreConnection, RealCoreConnection };
