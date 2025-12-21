from pathlib import Path
from io import BufferedReader
import asyncio


class VideoStreamer:

    def __init__(self, asset: Path, asset_dir: Path):
        self.video_file_path = asset_dir / "/".join(Path(asset).parts[1:])
        self.done = False
        self.file: BufferedReader | None = None

    def start(self) -> None:
        self.file = open(self.video_file_path, "rb")

    def stop(self) -> None:
        if self.file is None:
            raise RuntimeError(f"{self.video_file_path} not started")
        self.file.close()
        self.done = True

    def get_mimetype(self) -> str:
        return "video/webm"  # TODO: Depends on file

    def is_done(self) -> bool:
        return self.done

    async def get_chunk(self) -> bytes:
        # TODO: Does not handle multiple callers well
        # TODO: Vamp script makes separate audio and video, so the files from Zelda are like that
        #       - Why did we need that?
        #         * Because video and audio sample rates didn't add up?

        # We can send data as we go
        # Using it for pause:
        # - We would need to have a very small buffer on the client, is that safe?
        # - Need to duplicate the frame, can't just stop sending or the browser will try to compensate
        # Using it for vamp:
        # - Same, really, or we will get another loop if we switch too late
        # - This is inherent to the problem, let's just try it with some throttling
        # - need to go into the video to make sure we end on a frame? No, end of the file is already a frame boundary
        # - Still need to be aware of frames to make sure we don't go too far ahead
        #   * Either that, or send something from the frontend. But then the frontend controls the position, need to handle several
        #   * Need to handle reconnections? Keyframes...
        # - Is there some starting data we need to skip on files after the first?

        if self.file is None:
            raise RuntimeError(f"{self.video_file_path} not started")
        chunk_size = 100000
        chunk = self.file.read(chunk_size)  # TODO: async
        await asyncio.sleep(0.1)
        return chunk
