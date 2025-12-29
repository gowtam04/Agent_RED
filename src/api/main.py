"""FastAPI application for the Pokemon Red AI Agent dashboard."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import get_config
from ..engine import GameEngine
from .broadcaster import get_broadcaster
from .models import ControlCommand, GameStatus

logger = structlog.get_logger()

# Global engine instance
_engine: GameEngine | None = None

# Connected WebSocket clients
_connected_clients: set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global _engine

    config = get_config()
    _engine = GameEngine(config)

    # Register state update callback for WebSocket broadcasting
    _engine.on_state_update(broadcast_state)

    # Set event loop for broadcaster
    loop = asyncio.get_running_loop()
    get_broadcaster().set_event_loop(loop)

    # Register broadcaster listener for events/thoughts
    get_broadcaster().add_listener(broadcast_event)

    logger.info("Dashboard API started", port=config.dashboard_port)

    yield

    # Cleanup
    if _engine and _engine.state.running:
        await _engine.stop()

    logger.info("Dashboard API stopped")


# Create FastAPI app
app = FastAPI(
    title="Pokemon Red AI Agent Dashboard",
    description="Real-time dashboard for the Pokemon Red AI Agent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# REST ENDPOINTS
# ─────────────────────────────────────────────────────────────────


@app.get("/api/status")
async def get_status() -> GameStatus:
    """Get the current game engine status."""
    if _engine is None:
        return GameStatus(
            running=False,
            paused=False,
            current_mode="UNKNOWN",
            current_agent="none",
            total_frames=0,
            api_calls=0,
            uptime_seconds=0.0,
        )

    status = _engine.get_status()
    return GameStatus(**status)


@app.post("/api/start")
async def start_engine() -> dict[str, str]:
    """Start the game engine."""
    if _engine is None:
        return {"status": "error", "message": "Engine not initialized"}

    if _engine.state.running:
        return {"status": "already_running", "message": "Engine is already running"}

    await _engine.start()
    return {"status": "started", "message": "Game engine started"}


@app.post("/api/stop")
async def stop_engine() -> dict[str, str]:
    """Stop the game engine."""
    if _engine is None:
        return {"status": "error", "message": "Engine not initialized"}

    if not _engine.state.running:
        return {"status": "not_running", "message": "Engine is not running"}

    await _engine.stop()
    return {"status": "stopped", "message": "Game engine stopped"}


@app.post("/api/pause")
async def pause_engine() -> dict[str, str]:
    """Pause the game engine."""
    if _engine is None:
        return {"status": "error", "message": "Engine not initialized"}

    _engine.pause()
    return {"status": "paused", "message": "Game paused"}


@app.post("/api/resume")
async def resume_engine() -> dict[str, str]:
    """Resume the game engine."""
    if _engine is None:
        return {"status": "error", "message": "Engine not initialized"}

    _engine.resume()
    return {"status": "resumed", "message": "Game resumed"}


@app.post("/api/speed/{speed}")
async def set_speed(speed: int) -> dict[str, str]:
    """Set the emulation speed (0=unlimited, 1=normal, 2+=faster)."""
    if _engine is None:
        return {"status": "error", "message": "Engine not initialized"}

    _engine.set_speed(speed)
    return {"status": "ok", "message": f"Speed set to {speed}"}


@app.get("/api/history/thoughts")
async def get_thoughts(count: int = 20) -> dict[str, Any]:
    """Get recent agent thoughts."""
    thoughts = get_broadcaster().get_recent_thoughts(count)
    return {"thoughts": thoughts}


@app.get("/api/history/events")
async def get_events(count: int = 50) -> dict[str, Any]:
    """Get recent game events."""
    events = get_broadcaster().get_recent_events(count)
    return {"events": events}


# ─────────────────────────────────────────────────────────────────
# WEBSOCKET ENDPOINT
# ─────────────────────────────────────────────────────────────────


@app.websocket("/ws/game-state")
async def websocket_game_state(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time game state streaming."""
    await websocket.accept()
    _connected_clients.add(websocket)
    logger.info("WebSocket client connected", total_clients=len(_connected_clients))

    try:
        # Send initial history
        await websocket.send_json({
            "type": "HISTORY",
            "data": {
                "thoughts": get_broadcaster().get_recent_thoughts(20),
                "events": get_broadcaster().get_recent_events(50),
            },
        })

        # Handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                await handle_ws_message(websocket, json.loads(data))
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "PING"})

    except WebSocketDisconnect:
        _connected_clients.discard(websocket)
        logger.info("WebSocket client disconnected", total_clients=len(_connected_clients))
    except Exception as e:
        logger.warning("WebSocket error", error=str(e))
        _connected_clients.discard(websocket)


async def handle_ws_message(websocket: WebSocket, message: dict[str, Any]) -> None:
    """Handle incoming WebSocket messages."""
    msg_type = message.get("type")

    if msg_type == "PING":
        await websocket.send_json({"type": "PONG"})

    elif msg_type == "PONG":
        pass  # Client responding to our ping

    elif msg_type == "COMMAND":
        cmd_data = message.get("command", {})
        cmd = ControlCommand(**cmd_data)

        if _engine is None:
            await websocket.send_json({"type": "ERROR", "message": "Engine not initialized"})
            return

        if cmd.type == "PAUSE":
            _engine.pause()
        elif cmd.type == "RESUME":
            _engine.resume()
        elif cmd.type == "SET_SPEED":
            speed = cmd.payload.get("speed", 1) if cmd.payload else 1
            _engine.set_speed(speed)

        await websocket.send_json({"type": "COMMAND_ACK", "command": cmd.type})


async def broadcast_state(state_data: dict[str, Any]) -> None:
    """Broadcast state update to all connected WebSocket clients."""
    if not _connected_clients:
        return

    message = json.dumps({"type": "STATE_UPDATE", "data": state_data})

    disconnected: list[WebSocket] = []
    for client in _connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)

    # Remove disconnected clients
    for client in disconnected:
        _connected_clients.discard(client)


async def broadcast_event(msg_type: str, data: Any) -> None:
    """Broadcast event/thought to all connected WebSocket clients."""
    if not _connected_clients:
        return

    message = json.dumps({"type": msg_type, "data": data})

    disconnected: list[WebSocket] = []
    for client in _connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.append(client)

    # Remove disconnected clients
    for client in disconnected:
        _connected_clients.discard(client)


# ─────────────────────────────────────────────────────────────────
# STATIC FILES (FRONTEND)
# ─────────────────────────────────────────────────────────────────

# Get the path to the UI dist folder
_ui_dist = Path(__file__).parent.parent.parent / "ui" / "dist"
_assets_dir = _ui_dist / "assets"

# Log static file paths at startup
logger.info(
    "Static file paths",
    ui_dist=str(_ui_dist),
    ui_dist_exists=_ui_dist.exists(),
    assets_dir=str(_assets_dir),
    assets_exists=_assets_dir.exists(),
)


@app.get("/")
async def serve_index() -> FileResponse:
    """Serve the frontend index.html."""
    index_path = _ui_dist / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    # Return a simple HTML page if frontend not built
    return FileResponse(
        Path(__file__).parent / "fallback.html",
        media_type="text/html",
    )


# Mount static files if the assets folder exists
if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")
    logger.info("Mounted /assets static files", directory=str(_assets_dir))
else:
    logger.warning(
        "Assets directory not found - frontend may not be built",
        expected=str(_assets_dir),
        hint="Run: cd ui && npm install && npm run build",
    )


@app.get("/{path:path}")
async def serve_static(path: str) -> FileResponse:
    """Serve static files or fallback to index.html for SPA routing."""
    # Skip API routes - they're handled by explicit endpoints
    if path.startswith("api/") or path.startswith("ws/"):
        # Let FastAPI's 404 handler deal with unknown API routes
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")

    # Try to serve the exact file (e.g., vite.svg, robots.txt)
    file_path = _ui_dist / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)

    # SPA fallback - serve index.html for client-side routing
    index_path = _ui_dist / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    # Final fallback
    return FileResponse(
        Path(__file__).parent / "fallback.html",
        media_type="text/html",
    )
