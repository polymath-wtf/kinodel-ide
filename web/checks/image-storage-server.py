"""Owned browser fixture: real saved images/API, no workers/providers during reads."""
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import uvicorn
import backend.api as api
from backend.image_reads import image_projection
from backend.story_control import open_story_runtime
from tests.test_image_reads import ImageReadTests

api.PORT = int(sys.argv[1])
root = Path(os.environ['KINODEL_DATA_ROOT'])
metadata = root / 'image-browser-fixture.json'
library = root / 'characters'


async def seed():
    fixture = ImageReadTests()
    fixture.setUp()
    fixture.root, fixture.library = root, library
    try:
        async with fixture.source() as (runtime, ref, _):
            receipt = await fixture.start(runtime, ref)
            for index in range(3):
                fixture.unit(runtime.db, receipt.execution_id, index)
            fixture.publish(runtime.db, receipt)
            metadata.write_text(json.dumps(image_projection(runtime.db, receipt.execution_id).model_dump()), encoding='utf-8')
    finally:
        fixture.doCleanups()


if not metadata.exists():
    asyncio.run(seed())


@asynccontextmanager
async def readonly_lifespan(app):
    # Opening the existing saver/root is real. No run/sweep task is started.
    async with open_story_runtime(root, api.fixture_story, character_root=library) as runtime:
        app.state.runtime = runtime
        readonly = ImageReadTests()
        readonly.read_only(runtime.db)
        before = runtime.db.total_changes
        try:
            with patch('httpx.Client.send', side_effect=AssertionError('Provider forbidden')), \
                 patch('httpx.AsyncClient.send', side_effect=AssertionError('Provider forbidden')), \
                 patch('langgraph.pregel.Pregel.ainvoke', side_effect=AssertionError('Graph invocation forbidden')):
                yield
            assert runtime.db.total_changes == before, 'GET mutated real storage'
        finally:
            runtime.db.set_authorizer(None)


app = api.create_app(root, character_root=library)
app.router.lifespan_context = readonly_lifespan
uvicorn.run(app, host='127.0.0.1', port=api.PORT, workers=1, proxy_headers=False)
