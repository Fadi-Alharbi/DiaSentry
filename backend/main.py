"""
DiaSentry — FastAPI Backend Application
==========================================
Main entry point for the backend server. Exposes:

REST API:
  POST /api/log-meal        — Log a carbohydrate meal event
  POST /api/log-activity     — Log an exercise/activity event
  GET  /api/dashboard        — Get the current dashboard data (polling fallback)
  POST /api/chat             — Send a message to the AI chat assistant

WebSocket:
  /ws/live                   — Real-time glucose + analysis stream
  /ws/chat                   — Real-time chat with the AI assistant

The server manages the CGM simulator lifecycle and agent pipeline
via the lifespan context manager.
"""

import json
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Set

from backend.config import get_settings
from backend.simulator.streamer import streamer
from backend.simulator.models import MealEvent, ActivityEvent, ChatRequest
from backend.agents.workflow import run_agent_pipeline
from backend.agents.chat_agent import chat_agent
from backend.rag.knowledge_base import knowledge_base

# ═══════════════════════════════════════════════════════════════
#  Chat WebSocket Registry (for glucose push notifications)
# ═══════════════════════════════════════════════════════════════

# All active chat WebSocket connections — receives live glucose pushes
_chat_subscribers: Set[WebSocket] = set()

# ═══════════════════════════════════════════════════════════════
#  Logging Setup
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("DiaSentry.Main")


# ═══════════════════════════════════════════════════════════════
#  Application Lifespan (Startup / Shutdown)
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the application lifecycle:
      Startup: Initialize RAG knowledge base, connect agent pipeline, start CGM streamer
      Shutdown: Stop CGM streamer gracefully
    """
    settings = get_settings()

    logger.info("═" * 60)
    logger.info("  DiaSentry — Pro-Active AI Diabetes Management Platform")
    logger.info("═" * 60)

    # 1. Initialize RAG Knowledge Base
    logger.info("📚 Initializing ADA Clinical Guidelines knowledge base...")
    knowledge_base.initialize()

    # 2. Register the agent pipeline with the CGM streamer
    logger.info("🧠 Registering LangGraph agent pipeline...")
    streamer.set_agent_pipeline(run_agent_pipeline)

    # 3. Register glucose push callback → broadcasts live readings to chat clients
    async def _push_glucose_to_chat(payload: dict) -> None:
        """Push every new sensor reading to all connected chat WebSocket clients."""
        if not _chat_subscribers:
            return
        glucose = payload.get("glucose", "?")
        arrow   = payload.get("trend_arrow", "→")
        rate    = payload.get("rate_of_change", 0.0)
        urgency = payload.get("urgency_level", "stable")
        hypo    = payload.get("predicted_hypo", False)
        hyper   = payload.get("predicted_hyper", False)

        push_msg = json.dumps({
            "type": "glucose_update",
            "glucose": glucose,
            "trend_arrow": arrow,
            "rate_of_change": rate,
            "urgency_level": urgency,
            "predicted_hypo": hypo,
            "predicted_hyper": hyper,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, default=str)

        dead = set()
        for ws in list(_chat_subscribers):
            try:
                await ws.send_text(push_msg)
            except Exception:
                dead.add(ws)
        _chat_subscribers.difference_update(dead)

    streamer.set_chat_push_callback(_push_glucose_to_chat)

    # 4. Start the virtual CGM sensor
    logger.info(f"🏥 Starting Virtual CGM Sensor (interval={settings.SIM_INTERVAL_SEC}s)...")
    await streamer.start()

    logger.info("")
    logger.info("  🚀 DiaSentry is ONLINE and streaming!")
    logger.info(f"  📡 REST API:    http://{settings.HOST}:{settings.PORT}/api/dashboard")
    logger.info(f"  🔌 WebSocket:   ws://{settings.HOST}:{settings.PORT}/ws/live")
    logger.info(f"  💬 Chat WS:     ws://{settings.HOST}:{settings.PORT}/ws/chat")
    logger.info("═" * 60)

    yield  # Application is running

    # Shutdown
    logger.info("🛑 Shutting down DiaSentry...")
    await streamer.stop()
    logger.info("✅ DiaSentry stopped cleanly.")


# ═══════════════════════════════════════════════════════════════
#  FastAPI Application
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="DiaSentry — AI Diabetes Management Platform",
    version="1.0.0",
    description=(
        "Pro-active AI Agent platform for diabetes management. "
        "Features a Bergman Minimal Model CGM simulator, LangGraph multi-agent system "
        "with OpenAI function calling, and RAG over ADA clinical guidelines."
    ),
    lifespan=lifespan
)

# CORS — allow the frontend on any device to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
#  REST API Endpoints
# ═══════════════════════════════════════════════════════════════

@app.get("/api/health")
def health_check():
    """Health check and system info."""
    return {
        "system": "DiaSentry",
        "version": "1.0.0",
        "status": "online" if streamer.is_running else "stopped",
        "components": {
            "simulator": "Bergman Minimal Model",
            "agents": "LangGraph (Ingestion → Predictive → Recommendation)",
            "llm": "OpenAI Function Calling + ReAct",
            "rag": "ChromaDB + ADA Clinical Guidelines"
        }
    }


@app.post("/api/log-meal")
def log_meal(event: MealEvent):
    """
    Log a carbohydrate meal event.
    Dynamically alters the glucose simulation curve based on carbs + GI.
    """
    streamer.engine.inject_meal(
        carbs_g=event.carbs_g,
        glycemic_index=event.glycemic_index,
        food_name=event.food_name or "Meal"
    )

    logger.info(
        f"🍽️ Meal logged: {event.food_name or 'Meal'} — "
        f"{event.carbs_g}g carbs, GI={event.glycemic_index}"
    )

    return {
        "status": "meal_logged",
        "carbs_g": event.carbs_g,
        "glycemic_index": event.glycemic_index,
        "food_name": event.food_name,
        "timestamp": event.timestamp.isoformat()
    }


@app.post("/api/log-activity")
def log_activity(event: ActivityEvent):
    """
    Log an exercise/activity event.
    Dynamically alters the glucose simulation curve based on duration + intensity.
    """
    streamer.engine.inject_exercise(
        duration_min=event.duration_min,
        intensity=event.intensity,
        activity_name=event.activity_name or "Exercise"
    )

    logger.info(
        f"🏃 Activity logged: {event.activity_name or 'Exercise'} — "
        f"{event.duration_min}min, intensity={event.intensity}"
    )

    return {
        "status": "activity_logged",
        "duration_min": event.duration_min,
        "intensity": event.intensity,
        "activity_name": event.activity_name,
        "timestamp": event.timestamp.isoformat()
    }


@app.get("/api/dashboard")
def get_dashboard():
    """
    Get the current dashboard data.
    Polling fallback for clients that can't use WebSocket.
    """
    return streamer.build_dashboard_payload()


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Send a message to the AI chat assistant via REST.
    Returns the AI's contextual response.
    """
    # Update chat agent's patient context
    chat_agent.update_context(streamer.build_dashboard_payload())

    response = await chat_agent.process_message(request.message)

    return {
        "response": response,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ═══════════════════════════════════════════════════════════════
#  WebSocket Endpoints
# ═══════════════════════════════════════════════════════════════

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    Real-time glucose + analysis WebSocket stream.
    Clients receive a JSON payload on every CGM reading (every SIM_INTERVAL_SEC).

    Clients can also send events through the WebSocket:
      {"type": "log_meal", "carbs_g": 60, "glycemic_index": 70, "food_name": "Pizza"}
      {"type": "log_activity", "duration_min": 30, "intensity": 1.5}
    """
    await websocket.accept()
    streamer.add_subscriber(websocket)
    logger.info("🔌 WebSocket client connected (/ws/live)")

    try:
        # Send current state immediately on connect
        current = streamer.build_dashboard_payload()
        await websocket.send_text(json.dumps(current, default=str))

        while True:
            # Listen for incoming messages from the client
            data = await websocket.receive_text()
            if data:
                try:
                    msg = json.loads(data)
                    msg_type = msg.get("type", "")

                    if msg_type == "log_meal":
                        streamer.engine.inject_meal(
                            carbs_g=msg.get("carbs_g", 50),
                            glycemic_index=msg.get("glycemic_index", 55),
                            food_name=msg.get("food_name", "Meal")
                        )
                        await websocket.send_text(json.dumps({
                            "type": "event_ack",
                            "event": "meal_logged"
                        }))

                    elif msg_type == "log_activity":
                        streamer.engine.inject_exercise(
                            duration_min=msg.get("duration_min", 30),
                            intensity=msg.get("intensity", 1.0),
                            activity_name=msg.get("activity_name", "Exercise")
                        )
                        await websocket.send_text(json.dumps({
                            "type": "event_ack",
                            "event": "activity_logged"
                        }))

                except json.JSONDecodeError:
                    pass

    except WebSocketDisconnect:
        streamer.remove_subscriber(websocket)
        logger.info("🔌 WebSocket client disconnected (/ws/live)")


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    Real-time conversational AI chat WebSocket.
    Clients send text messages, receive AI responses.
    Also receives automatic glucose_update pushes on every sensor tick.

    Send:    {"message": "How will pizza affect my sugar?"}
    Receive: {"type": "chat_response", "response": "...", "timestamp": "..."}
    Receive: {"type": "glucose_update", "glucose": 112.4, "trend_arrow": "→", ...}
    """
    await websocket.accept()
    _chat_subscribers.add(websocket)
    logger.info(f"💬 Chat WebSocket connected (/ws/chat) — subscribers: {len(_chat_subscribers)}")

    # Send the latest glucose reading immediately on connect
    try:
        current = streamer.build_dashboard_payload()
        await websocket.send_text(json.dumps({
            "type": "glucose_update",
            "glucose": current.get("glucose", "?"),
            "trend_arrow": current.get("trend_arrow", "→"),
            "rate_of_change": current.get("rate_of_change", 0.0),
            "urgency_level": current.get("urgency_level", "stable"),
            "predicted_hypo": current.get("predicted_hypo", False),
            "predicted_hyper": current.get("predicted_hyper", False),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, default=str))
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                user_message = msg.get("message", "")

                if user_message:
                    # Always fetch the absolute latest reading before answering
                    chat_agent.update_context(streamer.build_dashboard_payload())

                    # Send typing indicator
                    await websocket.send_text(json.dumps({"type": "typing", "is_typing": True}))

                    # Process the message with the local AI model
                    response = await chat_agent.process_message(user_message)

                    # Clear typing indicator + send response
                    await websocket.send_text(json.dumps({"type": "typing", "is_typing": False}))
                    await websocket.send_text(json.dumps({
                        "type": "chat_response",
                        "response": response,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))

    except WebSocketDisconnect:
        _chat_subscribers.discard(websocket)
        logger.info(f"💬 Chat WebSocket disconnected (/ws/chat) — subscribers: {len(_chat_subscribers)}")


# ═══════════════════════════════════════════════════════════════
#  Static Frontend Serving (For Hugging Face Spaces / Docker)
# ═══════════════════════════════════════════════════════════════
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    logger.info(f"🎨 Serving static React frontend from {frontend_dist}")


# ═══════════════════════════════════════════════════════════════
#  Entry Point
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info"
    )
