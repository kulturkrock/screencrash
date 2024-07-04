import * as React from "react";
import * as d3 from "d3";

import { INodeCollection, INodeChoice, IAction } from "./types";
import style from "../less/timeline.module.less";

const VIEWBOX_WIDTH = 200;
const LEFT_MARGIN = 30;

const NODE_SPACING = 40;
const NODE_RADIUS = 5;

const CHOICE_SPACING = 25;
const CHOICE_INDENT = 10;
const CHOICE_CURVITUDE = 25;

const CURRENT_NODE_FILL = "wheat";
const BACKGROUND_COLOR = "rgb(75, 14, 14)";

interface IProps {
  nodes: INodeCollection;
  history: string[];
  focusY: number;
  choiceKeys: string[];
  showActions: boolean;
}

interface IState {
  id: string;
  viewboxHeight: number;
  scale: number;
}

class Timeline extends React.PureComponent<IProps, IState> {
  public constructor(props: IProps) {
    super(props);
    // Create a random ID, to avoid collisions if we ever have multiple
    // timelines.
    this.state = {
      id: `timeline${Math.round(Math.random() * 10000000)}`,
      viewboxHeight: 0,
      scale: 1,
    };
  }

  public componentDidMount(): void {
    this.calculateViewboxHeight();
    this.updateTimeline(this.props.nodes, this.props.history);
  }

  public componentDidUpdate(): void {
    this.updateTimeline(this.props.nodes, this.props.history);
  }

  private calculateViewboxHeight(): void {
    const { height, width } = document
      .getElementById(this.state.id)
      .getBoundingClientRect();
    const viewboxHeight = (height - 2) * (VIEWBOX_WIDTH / (width - 2));
    // This will only grow the viewbox, never shrink it.
    // Since we only do it when mounting it's fine for now.
    this.setState({
      viewboxHeight,
      scale: viewboxHeight / height,
    });
  }

  public updateTimeline(nodes: INodeCollection, history: string[]): void {
    const focusY = this.props.focusY * this.state.scale;
    // Enough nodes before and after that the first and last are out of view
    const nodesAfter =
      Math.round((this.state.viewboxHeight - focusY) / NODE_SPACING) + 1;
    const nodesBefore = Math.round(focusY / NODE_SPACING) + 1;
    const firstNodeY = focusY - nodesBefore * NODE_SPACING;
    // Show the recent history
    const visibleNodes = history
      .slice(-nodesBefore - 1, -1)
      .map((id) => ({ id, tense: "past", ...nodes[id] }));
    if (history.length > 0) {
      // Show the current node
      const currentId = history[history.length - 1];
      visibleNodes.push({
        id: currentId,
        tense: "present",
        ...nodes[currentId],
      });
      // Show a few nodes into the future, or until we reach a branch point
      for (let step = 0; step < nodesAfter; step++) {
        const nextId = visibleNodes[visibleNodes.length - 1].next;
        if (typeof nextId === "string" && nodes[nextId] !== undefined) {
          visibleNodes.push({ id: nextId, tense: "future", ...nodes[nextId] });
        }
      }
    }
    const pastNodes = visibleNodes.filter(({ tense }) => tense === "past")
      .length;
    const nodesWithPosition = visibleNodes.map((node, index) => ({
      distanceFromStart: Math.max(history.length - nodesBefore - 1, 0) + index,
      x: LEFT_MARGIN,
      y: firstNodeY + (index + nodesBefore - pastNodes) * NODE_SPACING,
      ...node,
    }));
    // Add lines between the nodes
    const lines: {
      id: string;
      startX: number;
      startY: number;
      endX: number;
      endY: number;
    }[] = [];
    nodesWithPosition.forEach((node, i) => {
      if (i < nodesWithPosition.length - 1) {
        const nextNode = nodesWithPosition[i + 1];
        lines.push({
          id: `${node.id}:${node.distanceFromStart}-${nextNode.id}:${nextNode.distanceFromStart}`,
          startX: node.x,
          startY: node.y,
          endX: nextNode.x,
          endY: nextNode.y,
        });
      }
    });
    const transition = d3.transition().duration(300).ease(d3.easeQuadOut);
    // Draw the lines
    d3.select(`#${this.state.id}`)
      .select("svg")
      .selectAll("#node-line")
      .data(lines, ({ id }) => id)
      .join(
        (enter) =>
          enter
            .append("line")
            .attr("id", "node-line")
            .attr("x1", ({ startX }) => startX)
            .attr("y1", ({ startY }) => startY)
            .attr("x2", ({ endX }) => endX)
            .attr("y2", ({ endY }) => endY)
            .classed(style.line, true)
            .lower(),
        (update) => {
          update
            .transition(transition)
            .attr("x1", ({ startX }) => startX)
            .attr("y1", ({ startY }) => startY)
            .attr("x2", ({ endX }) => endX)
            .attr("y2", ({ endY }) => endY);
          return update;
        },
      );
    // Then draw the nodes
    d3.select(`#${this.state.id}`)
      .select("svg")
      .selectAll("g")
      .data(
        nodesWithPosition,
        // Construct a unique ID from the actual node ID and its distance from
        // the starting point, to let d3 keep track of nodes between updates.
        // We cannot use the actual ID since nodes can repeat.
        // Once we can have branching paths, this may have to refined further.
        ({ id, distanceFromStart }) => `${id}:${distanceFromStart}`,
      )
      .join(
        (enter) => {
          const g = enter.append("g");
          g.append("circle")
            .attr("id", "node")
            .attr("cx", ({ x }) => x)
            .attr("cy", ({ y }) => y)
            .attr("r", NODE_RADIUS)
            .classed(style.node, true)
            .classed(style.currentNode, ({ tense }) => tense === "present")
            .attr("fill", ({ tense }) =>
              tense === "present" ? CURRENT_NODE_FILL : BACKGROUND_COLOR,
            );
          g.append("foreignObject")
            .attr("id", "lineNumber")
            .attr("x", 0)
            .attr("y", ({ y }) => y - NODE_SPACING / 2)
            .attr("width", LEFT_MARGIN - NODE_RADIUS)
            .attr("height", NODE_SPACING)
            .append("xhtml:div")
            .classed(style.lineNumber, true)
            .text(({ lineNumber }) => lineNumber);

          const promptContainer = g
            .append("foreignObject")
            .attr("id", "prompt")
            .attr("x", ({ x }) => x + NODE_RADIUS)
            .attr("y", ({ y }) => y - NODE_SPACING / 2)
            .attr("width", ({ x }) => VIEWBOX_WIDTH - x - NODE_RADIUS)
            .attr("height", NODE_SPACING)
            .append("xhtml:div")
            .classed(style.prompt, true);

          promptContainer
            .append("xhtml:div")
            .classed(style.promptText, true)
            .html(({ prompt }) => boldBetweenBrackets(prompt));
          promptContainer
            .selectAll(`.${style.promptAction}`)
            .data(({ actions }) => actions)
            .enter()
            .append("xhtml:div")
            .classed(style.promptAction, true)
            .classed(style.promptActionHidden, !this.props.showActions)
            .text((action) => getActionText(action));

          this.props.choiceKeys.forEach((key, i) => {
            const subGroup = g.filter(
              ({ next }) => Array.isArray(next) && next.length > i,
            );
            subGroup
              .append("circle")
              .attr("id", `circle-choice-${key}`)
              .attr("cx", ({ x }) => x + CHOICE_INDENT)
              .attr("cy", ({ y }) => y + CHOICE_SPACING * (i + 1))
              .attr("r", NODE_RADIUS)
              .classed(style.node, true)
              .attr("opacity", ({ tense }) =>
                tense === "present" || tense === "future" ? 1 : 0,
              )
              .attr("fill", BACKGROUND_COLOR);
            const promptContainer = subGroup
              .append("foreignObject")
              .attr("id", `text-choice-${key}`)
              .attr("x", ({ x }) => x + CHOICE_INDENT + NODE_RADIUS)
              .attr(
                "y",
                ({ y }) => y + CHOICE_SPACING * (i + 1) - CHOICE_SPACING / 2,
              )
              .attr(
                "width",
                ({ x }) => VIEWBOX_WIDTH - x - (CHOICE_INDENT + NODE_RADIUS),
              )
              .attr("height", CHOICE_SPACING)
              .attr("opacity", ({ tense }) =>
                tense === "present" || tense === "future" ? 1 : 0,
              )
              .append("xhtml:div")
              .classed(style.prompt, true);
            promptContainer
              .append("xhtml:div")
              .classed(style.promptText, true)
              .text(
                ({ next }) =>
                  `[${key}]: ${(next as INodeChoice[])[i].description}`,
              );
            promptContainer
              .selectAll(`.${style.promptAction}`)
              .data(({ next }) => (next as INodeChoice[])[i].actions)
              .enter()
              .append("xhtml:div")
              .classed(style.promptAction, true)
              .classed(style.promptActionHidden, !this.props.showActions)
              .text((action) => getActionText(action));
            subGroup
              .append("path")
              .attr("id", `line-choice-${key}`)
              .attr(
                "d",
                ({ x, y }) =>
                  `M ${x} ${y} ` +
                  `C ${x} ${y + CHOICE_CURVITUDE * (i + 1)}, ` +
                  `${x} ${y + CHOICE_CURVITUDE * (i + 1)}, ` +
                  `${x + CHOICE_INDENT} ${y + CHOICE_SPACING * (i + 1)}`,
              )
              .classed(style.line, true)
              .attr("fill", "none")
              .attr("opacity", ({ tense }) =>
                tense === "present" || tense === "future" ? 1 : 0,
              )
              .lower();
          });
          return g;
        },
        (update) => {
          update
            .select("#node")
            .classed(style.currentNode, ({ tense }) => tense === "present")
            .transition(transition)
            .attr("cx", ({ x }) => x)
            .attr("cy", ({ y }) => y)
            .attr("fill", ({ tense }) =>
              tense === "present" ? CURRENT_NODE_FILL : BACKGROUND_COLOR,
            );
          update
            .select("#prompt")
            .transition(transition)
            .attr("x", ({ x }) => x + NODE_RADIUS)
            .attr("y", ({ y }) => y - NODE_SPACING / 2);
          update
            .selectAll(`.${style.promptAction}`)
            .classed(style.promptActionHidden, !this.props.showActions);
          update
            .select("#lineNumber")
            .transition(transition)
            .attr("x", 0)
            .attr("y", ({ y }) => y - NODE_SPACING / 2);

          this.props.choiceKeys.forEach((key, i) => {
            update
              .select(`#line-choice-${key}`)
              .transition(transition)
              .attr(
                "d",
                ({ x, y }) =>
                  `M ${x} ${y} ` +
                  `C ${x} ${y + CHOICE_CURVITUDE * (i + 1)}, ` +
                  `${x} ${y + CHOICE_CURVITUDE * (i + 1)}, ` +
                  `${x + CHOICE_INDENT} ${y + CHOICE_SPACING * (i + 1)}`,
              )
              .attr("opacity", ({ tense }) =>
                tense === "present" || tense === "future" ? 1 : 0,
              );
            update
              .select(`#circle-choice-${key}`)
              .transition(transition)
              .attr("cx", ({ x }) => x + CHOICE_INDENT)
              .attr("cy", ({ y }) => y + CHOICE_SPACING * (i + 1))
              .attr("opacity", ({ tense }) =>
                tense === "present" || tense === "future" ? 1 : 0,
              );
            update
              .select(`#text-choice-${key}`)
              .transition(transition)
              .attr("x", ({ x }) => x + CHOICE_INDENT + NODE_RADIUS)
              .attr(
                "y",
                ({ y }) => y + CHOICE_SPACING * (i + 1) - CHOICE_SPACING / 2,
              )
              .attr("opacity", ({ tense }) =>
                tense === "present" || tense === "future" ? 1 : 0,
              );
          });
          return update;
        },
      );
  }

  public render(): JSX.Element {
    return (
      <div className={style.container} id={this.state.id}>
        <svg viewBox={`0 0 ${VIEWBOX_WIDTH} ${this.state.viewboxHeight}`}></svg>
      </div>
    );
  }
}

function getActionText(action: IAction): string {
  if (action.desc != null) {
    return action.desc;
  } else if (action.params && action.params.entityId) {
    return `${action.target}:${action.cmd} ${action.params.entityId}`;
  } else {
    return `${action.target}:${action.cmd}`;
  }
}

function boldBetweenBrackets(text: string): string {
  return text
    .replace("[", '<span style="font-weight:bold;">[')
    .replace("]", "]</span>");
}

export { Timeline };
