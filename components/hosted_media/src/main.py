import asyncio
import aiohttp.web
import os

from web_app import get_app


async def main():

    app = get_app()

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(
        runner, port=os.environ.get("SCREENCRASH_HOSTED_MEDIA_PORT", 8123)
    )
    await site.start()

    # wait forever
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
