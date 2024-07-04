interface PredefinedActionsTrigger {
  messageType: string;
  actions: string[];
}
interface OnTheFlyAction {
  messageType: string;
  target_component: string;
  cmd: string;
  assets: string[];
  params: { [key: string]: unknown };
}
interface ComponentResetMessage {
  messageType: string;
  componentId: string;
}
interface ComponentRestartMessage {
  messageType: string;
  componentId: string;
}

export {
  PredefinedActionsTrigger,
  OnTheFlyAction,
  ComponentResetMessage,
  ComponentRestartMessage,
};
