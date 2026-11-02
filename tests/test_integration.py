import asyncio
import json
import unittest
import websockets
from backend.app import VirtualKeyboardBackend
from backend.config import WS_HOST, WS_PORT


class TestIntegrationWebSocket(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = VirtualKeyboardBackend()
        self.backend.initialize()
        self.server = await websockets.serve(self.backend.client_handler, WS_HOST, WS_PORT)
        # Background task for broadcasting
        self.broadcast_task = asyncio.create_task(self.backend.broadcast_loop())

    async def asyncTearDown(self):
        self.backend.running = False
        self.broadcast_task.cancel()
        self.server.close()
        await self.server.wait_closed()
        self.backend.shutdown()

    async def test_full_websocket_communication(self):
        uri = f"ws://{WS_HOST}:{WS_PORT}"
        async with websockets.connect(uri) as ws:
            # 1. Receive initial configuration
            init_msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            data = json.loads(init_msg)
            self.assertEqual(data.get("type"), "init")
            self.assertTrue(len(data.get("keys")) > 0)

            # 2. Test toggle OS input command
            await ws.send(json.dumps({"action": "toggle_os_input", "enabled": False}))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
            self.assertEqual(resp.get("type"), "os_input_status")
            self.assertFalse(resp.get("enabled"))

            # 3. Test start data collection command
            await ws.send(json.dumps({"action": "start_collection", "key_label": "SPACE"}))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=3.0))
            self.assertEqual(resp.get("type"), "collection_status")
            self.assertTrue(resp.get("collecting"))

            # 4. Test model training command (.pkl)
            await ws.send(json.dumps({"action": "train_model"}))
            resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=6.0))
            self.assertEqual(resp.get("type"), "train_result")
            self.assertTrue(resp["result"]["success"])

            # 5. Receive real-time tick frame
            tick_msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            tick_data = json.loads(tick_msg)
            self.assertEqual(tick_data.get("type"), "tick")
            self.assertIn("preview_frame", tick_data)


if __name__ == "__main__":
    unittest.main()

