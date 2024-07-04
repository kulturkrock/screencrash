import * as React from "react";

import style from "../less/statusView.module.less";
import { InventoryView } from "./components/inventory";
import { ComponentView } from "./componentView";
import { OnTheFlyAction } from "./coreMessages";
import { EffectView } from "./effectView/effectView";
import { LogView } from "./logView";
import { ShortcutView } from "./shortcutView";
import {
  IComponentState,
  IEffect,
  IEffectActionEvent,
  ILogMessage,
  INodeCollection,
  IUIConfig,
} from "./types";

interface ITab {
  key: string;
  name: string;
  icon: JSX.Element;
  count?: number;
}

const tabs = {
  effects: "effects",
  components: "components",
  logs: "log",
  inventory: "inventory",
  shortcuts: "shortcuts",
};

interface IProps {
  uiConfig: IUIConfig;
  effects: IEffect[];
  nodes: INodeCollection;
  onOnTheFlyAction: (action: OnTheFlyAction) => void;
  onTriggerPredefinedActions: (actions: string[]) => void;
  onSendUIMessage: (
    messageType: string,
    params: { [index: string]: unknown },
  ) => void;
  onEffectAction: (event: IEffectActionEvent) => void;
  onComponentReset: (componentId: string) => void;
  onComponentRestart: (componentId: string) => void;
  components: IComponentState[];
  logMessages: ILogMessage[];
  onClearLogMessages: () => void;
}

interface IPropsTab {
  tabName: string;
  props: IProps;
}

interface IState {
  currentTab: string;
  availableTabs: ITab[];
}

class StatusView extends React.PureComponent<IProps, IState> {
  constructor(props: IProps) {
    super(props);
    this.state = {
      currentTab: tabs.effects,
      availableTabs: this.createAvailableTabs(),
    };

    this.handleKey = this.handleKey.bind(this);
  }

  public componentDidMount(): void {
    document.addEventListener("keydown", this.handleKey);
  }

  public componentWillUnmount(): void {
    document.removeEventListener("keydown", this.handleKey);
  }

  public componentDidUpdate(): void {
    const newTabs = this.createAvailableTabs();
    if (this.state.availableTabs.length === newTabs.length) {
      const changedTabs = this.state.availableTabs.filter((tab, index) => {
        return (
          tab.key !== newTabs[index].key || tab.count !== newTabs[index].count
        );
      });
      if (changedTabs.length === 0) {
        // Avoid recursive updates without changes.
        return;
      }
    }

    this.setState({ availableTabs: newTabs });
  }

  public createAvailableTabs(): ITab[] {
    const result: ITab[] = [
      {
        key: tabs.effects,
        name: "Effects",
        icon: <span className={style.shortName}>FX</span>,
        count: this.props.effects.length,
      },
      {
        key: tabs.components,
        name: "Components",
        icon: <span className={style.shortName}>COMP</span>,
        count: this.props.components.length,
      },
      {
        key: tabs.shortcuts,
        name: "Shortcuts",
        icon: <span className={style.shortName}>SC</span>,
      },
      {
        key: tabs.logs,
        name: "Logs",
        icon: <span className={style.shortName}>LOG</span>,
        count: this.props.logMessages.length,
      },
    ];

    if (
      this.props.components.filter(
        (comp) => comp.info.componentName === "inventory",
      ).length !== 0
    ) {
      result.push({
        key: tabs.inventory,
        name: "Inventory",
        icon: <span className={style.shortName}>INV</span>,
      });
    }

    return result;
  }

  public render(): JSX.Element {
    return (
      <div className={style.container}>
        <div className={style.tabBar}>
          {this.state.availableTabs.map((tab) => (
            <div
              key={tab.key}
              className={`${style.tab} ${
                this.state.currentTab == tab.key ? style.selected : ""
              }`}
              onClick={this.setTab.bind(this, tab.key)}
            >
              {this.state.currentTab === tab.key ? (
                tab.name + (tab.count !== undefined ? ` (${tab.count})` : "")
              ) : (
                <div>
                  {tab.icon} {tab.count !== undefined ? `(${tab.count})` : ""}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className={style.tabContent}>
          <TabContent tabName={this.state.currentTab} props={this.props} />
        </div>
      </div>
    );
  }

  public setTab(tabName: string): void {
    this.setState({ ...this.state, currentTab: tabName });
  }

  private handleKey(event: KeyboardEvent) {
    // Only accept keyboard shortcuts when nothing is focused
    if (document.activeElement === document.body && !event.repeat) {
      const keyAsNum = event.key.charCodeAt(0) - "0".charCodeAt(0);
      if (
        keyAsNum >= 1 &&
        keyAsNum <= 9 &&
        keyAsNum - 1 < this.state.availableTabs.length
      ) {
        this.setTab(this.state.availableTabs[keyAsNum - 1].key);
      }
    }
  }
}

function TabContent(propsData: IPropsTab): JSX.Element {
  if (propsData.tabName === tabs.effects) {
    return (
      <EffectView
        effects={propsData.props.effects}
        onEffectAction={propsData.props.onEffectAction}
      />
    );
  } else if (propsData.tabName == tabs.components) {
    return (
      <ComponentView
        components={propsData.props.components}
        onReset={propsData.props.onComponentReset}
        onRestart={propsData.props.onComponentRestart}
      />
    );
  } else if (propsData.tabName == tabs.logs) {
    return (
      <LogView
        logMessages={propsData.props.logMessages}
        onClearMessages={propsData.props.onClearLogMessages}
      />
    );
  } else if (propsData.tabName === tabs.shortcuts) {
    return (
      <ShortcutView
        shortcuts={propsData.props.uiConfig.shortcuts}
        nodes={propsData.props.nodes}
        onSendUIMessage={propsData.props.onSendUIMessage}
        onTriggerPredefinedActions={propsData.props.onTriggerPredefinedActions}
      />
    );
  } else if (propsData.tabName === tabs.inventory) {
    const inventoryComponents = propsData.props.components.filter(
      (comp) => comp.info.componentName === "inventory",
    );
    if (inventoryComponents.length > 0) {
      return (
        <InventoryView
          inventory={inventoryComponents[0]}
          onOnTheFlyAction={propsData.props.onOnTheFlyAction}
        />
      );
    } else {
      return <div>Error. Could not find any inventory</div>;
    }
  }
  return null;
}

export { StatusView };
