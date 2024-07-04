import * as React from "react";

import style from "../../less/effectView.module.less";

interface IState {
  lastUpdated: number;
  currentTime: number;
  showMarker: boolean;
  markerTime: number;
}

interface IProps {
  onClicked: (time: number) => void;
  currentTime: number;
  lastUpdated: number;
  duration: number;
  looping: boolean;
  running: boolean;
}

class ProgressBar extends React.PureComponent<IProps, IState> {
  timerID: number;

  constructor(props: IProps) {
    super(props);
    this.state = {
      currentTime: this.props.currentTime,
      lastUpdated: this.props.lastUpdated,
      showMarker: false,
      markerTime: 0,
    };
  }

  componentDidMount(): void {
    this.timerID = setInterval(() => this.updateTime(), 200);
  }

  componentWillUnmount(): void {
    clearInterval(this.timerID);
  }

  public render(): JSX.Element {
    return (
      <div
        className={style.progressBarWrapper}
        onMouseOver={this.onMouseOver.bind(this)}
        onMouseOut={this.onMouseOut.bind(this)}
        onMouseMove={this.onMouseMove.bind(this)}
        onClick={this.onClick.bind(this)}
      >
        <div
          className={style.progressBar}
          style={{ width: `${this.barWidth()}%` }}
        ></div>
        <div className={style.progressBarText}>{this.getLabel()}</div>
      </div>
    );
  }

  public updateTime(): void {
    const now = Date.now();
    let currentTime = this.state.currentTime;
    let lastUpdated = this.state.lastUpdated;
    let hasUpdateFromBackend = false;
    if (this.state.lastUpdated < this.props.lastUpdated) {
      currentTime = this.props.currentTime;
      lastUpdated = this.props.lastUpdated;
      hasUpdateFromBackend = true;
    }

    if (this.props.running) {
      const timeDiff = now - lastUpdated;
      let newTime = currentTime + timeDiff / 1000;
      if (this.props.looping) {
        newTime = newTime % this.props.duration;
      } else {
        newTime = Math.min(newTime, this.props.duration);
      }

      this.setState({
        ...this.state,
        lastUpdated: now,
        currentTime: newTime,
      });
    } else {
      if (hasUpdateFromBackend) {
        this.setState({
          ...this.state,
          lastUpdated: now,
          currentTime: currentTime,
        });
      } else {
        this.setState({ ...this.state, lastUpdated: now });
      }
    }
  }

  public getLabel(): string {
    return (
      getTimeAsMinutes(this.state.currentTime) +
      " / " +
      getTimeAsMinutes(this.props.duration)
    );
  }

  public barWidth(): number {
    if (this.props.duration == 0) {
      return 100;
    }

    return Math.round((this.state.currentTime / this.props.duration) * 100);
  }

  public onMouseOver(): void {
    this.setState({ ...this.state, showMarker: true });
  }

  public onMouseOut(): void {
    this.setState({ ...this.state, showMarker: false });
  }

  public onMouseMove(event: React.MouseEvent<HTMLElement>): void {
    const { x, width } = event.currentTarget.getBoundingClientRect();
    const elementX = event.clientX - x;
    const time = this.props.duration * (elementX / width);
    this.setState({
      ...this.state,
      markerTime: time,
    });
  }

  public onClick(): void {
    if (this.state.showMarker) {
      this.props.onClicked(this.state.markerTime);
    }
  }
}

function getTimeAsMinutes(seconds: number): string {
  return (
    getNumAsTwoDigit(Math.floor(seconds / 60)) +
    ":" +
    getNumAsTwoDigit(Math.floor(seconds % 60))
  );
}

function getNumAsTwoDigit(num: number): string {
  return (num < 10 ? "0" : "") + num;
}

export { ProgressBar };
