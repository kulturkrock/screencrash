interface IAction {
  target: string;
  cmd: string;
  desc: string;
  params: { [index: string]: unknown };
}
interface INodeChoice {
  node: string;
  description: string;
  actions: IAction[];
}
interface INode {
  next: string | INodeChoice[];
  actions: IAction[];
  prompt: string;
  pdfPage: number;
  pdfLocationOnPage: number;
  lineNumber: number | undefined;
}

interface INodeCollection {
  [index: string]: INode;
}

interface IShortcut {
  title: string;
  hotkey: string | undefined;
  actions: string[];
}

interface IUIConfig {
  shortcuts: IShortcut[];
}

enum EffectType {
  Other,
  Audio,
  Video,
  Image,
  WebPage,
}

interface IEffect {
  entityId: string;
  name: string;
  type: EffectType;
  duration?: number;
  currentTime?: number;
  lastSync?: number;
  playing?: boolean;
  looping?: boolean;
  muted?: boolean;
  volume?: number;
  visible?: boolean;
  currentImage?: string;
}

interface IEffectActionEvent {
  entityId: string;
  action_type: string;
  media_type: string;
  value?: string;
  numericValue?: number;
}

interface IComponentInfo {
  componentId: string;
  componentName: string;
  status: string;
}

interface IComponentState {
  info: IComponentInfo;
  state: { [index: string]: unknown };
}

interface IConnectionState {
  connected: boolean;
}

interface ILogMessage {
  level: string;
  timestamp: number;
  origin: string;
  message: string;
}

// Empty object, since there is no built-in for it
type IEmpty = Record<never, never>;

export {
  INodeChoice,
  IAction,
  INode,
  INodeCollection,
  IShortcut,
  IUIConfig,
  IEffect,
  EffectType,
  IEffectActionEvent,
  IComponentInfo,
  IComponentState,
  IConnectionState,
  ILogMessage,
  IEmpty,
};
