from pathlib import Path


class VideoStreamer:

    def __init__(self, asset: Path):
        self.video_file = asset

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
