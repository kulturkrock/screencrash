import asyncio
import aiohttp.web
import os

from web_app import get_app
from entity_manager import EntityManager
from core_connection import core_connection
from uuid import uuid4


async def main():

    component_id = str(uuid4())
    entity_manager = EntityManager(component_id)

    app = get_app(entity_manager)

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(
        runner, port=int(os.environ.get("SCREENCRASH_HOSTED_MEDIA_PORT", "8123"))
    )
    await site.start()

    # wait forever
    await core_connection(
        os.environ.get("SCREENCRASH_HOSTED_MEDIA_CORE_ADDRESS", "localhost:8001"),
        entity_manager,
    )


if __name__ == "__main__":
    asyncio.run(main())
