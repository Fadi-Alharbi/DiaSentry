"""
DiaSentry — Async CGM Streamer
================================
Background task that runs the Bergman engine at the configured interval,
pushes readings to all WebSocket subscribers, and triggers the
LangGraph agent pipeline on each reading.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set, Any, Optional, Callable, Awaitable, List

from backend.config import get_settings
from backend.simulator.engine import BergmanEngine
from backend.simulator.models import GlucoseReading, DashboardPayload, TrendDirection

logger = logging.getLogger("DiaSentry.Simulator.Streamer")


class CGMStreamer:
    """
    Manages the virtual CGM sensor lifecycle:
      1. Runs the BergmanEngine at SIM_INTERVAL_SEC real-time intervals
      2. Broadcasts each reading + agent analysis to WebSocket subscribers
      3. Maintains the single source of truth for current patient state

    Usage:
        streamer = CGMStreamer()
        streamer.set_agent_pipeline(my_pipeline_fn)
        await streamer.start()
    """

    def __init__(self):
        self.engine = BergmanEngine()
        self._subscribers: Set[Any] = set()
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._agent_pipeline: Optional[Callable] = None

        # Latest analysis from the agent pipeline (cached for REST API access)
        self.latest_analysis: dict = {}
        self.latest_reading: Optional[GlucoseReading] = None

        # Optional async callback to push glucose updates to chat clients
        self._chat_push_callback: Optional[Callable] = None

    # ═══════════════════════════════════════════════════════════
    #  Subscriber Management
    # ═══════════════════════════════════════════════════════════

    def add_subscriber(self, ws: Any) -> None:
        """Register a WebSocket client for live updates."""
        self._subscribers.add(ws)
        logger.info(f"WebSocket subscriber added. Total: {len(self._subscribers)}")

    def remove_subscriber(self, ws: Any) -> None:
        """Unregister a WebSocket client."""
        self._subscribers.discard(ws)
        logger.info(f"WebSocket subscriber removed. Total: {len(self._subscribers)}")

    async def _broadcast(self, data: dict) -> None:
        """Send data to all connected WebSocket clients. Remove dead connections."""
        if not self._subscribers:
            return

        dead = set()
        message = json.dumps(data, default=str)

        for ws in self._subscribers:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        self._subscribers -= dead
        if dead:
            logger.info(f"Removed {len(dead)} dead WebSocket connection(s)")

    # ═══════════════════════════════════════════════════════════
    #  Agent Pipeline Integration
    # ═══════════════════════════════════════════════════════════

    def set_agent_pipeline(self, pipeline_fn: Callable) -> None:
        """
        Set the LangGraph agent pipeline function.
        Signature: async def pipeline(reading, history, engine) -> dict
        """
        self._agent_pipeline = pipeline_fn
        logger.info("Agent pipeline registered with CGM streamer")

    def set_chat_push_callback(self, callback: Callable) -> None:
        """
        Register an async callback that receives every new dashboard payload.
        Used by main.py to push live glucose readings to chat WebSocket clients.
        Signature: async def callback(payload: dict) -> None
        """
        self._chat_push_callback = callback
        logger.info("Chat push callback registered with CGM streamer")

    # ═══════════════════════════════════════════════════════════
    #  Trend Computation
    # ═══════════════════════════════════════════════════════════

    def _compute_trend(self, readings: List[GlucoseReading]) -> tuple:
        """
        Compute the trend direction and rate of change from recent readings.
        Uses weighted average of the last 3 readings for smoothness.

        Returns: (TrendDirection, rate_mg_dl_per_min, trend_arrow_symbol)
        """
        if len(readings) < 2:
            return TrendDirection.STABLE, 0.0, "→"

        # Use up to last 3 readings for a smoothed rate
        recent = readings[-min(4, len(readings)):]
        current = recent[-1].glucose_mg_dl

        # Weighted rate calculation
        rates = []
        for i, r in enumerate(recent[:-1]):
            # Each reading is 5 minutes apart
            steps_back = len(recent) - 1 - i
            time_delta = steps_back * 5.0  # minutes
            if time_delta > 0:
                rate = (current - r.glucose_mg_dl) / time_delta
                weight = i + 1  # More recent = higher weight
                rates.append((rate, weight))

        if not rates:
            return TrendDirection.STABLE, 0.0, "→"

        weighted_rate = sum(r * w for r, w in rates) / sum(w for _, w in rates)

        # Classify per CGM standards
        if weighted_rate > 3.0:
            return TrendDirection.RAPIDLY_RISING, weighted_rate, "↑↑"
        elif weighted_rate > 2.0:
            return TrendDirection.RISING, weighted_rate, "↑"
        elif weighted_rate > 1.0:
            return TrendDirection.SLIGHTLY_RISING, weighted_rate, "↗"
        elif weighted_rate > -1.0:
            return TrendDirection.STABLE, weighted_rate, "→"
        elif weighted_rate > -2.0:
            return TrendDirection.SLIGHTLY_FALLING, weighted_rate, "↘"
        elif weighted_rate > -3.0:
            return TrendDirection.FALLING, weighted_rate, "↓"
        else:
            return TrendDirection.RAPIDLY_FALLING, weighted_rate, "↓↓"

    def _compute_tir(self, readings: List[GlucoseReading]) -> float:
        """Compute Time-in-Range percentage (70-180 mg/dL)."""
        if not readings:
            return 0.0
        settings = get_settings()
        in_range = sum(
            1 for r in readings
            if settings.TARGET_LOW <= r.glucose_mg_dl <= settings.TARGET_HIGH
        )
        return round((in_range / len(readings)) * 100, 1)

    # ═══════════════════════════════════════════════════════════
    #  Build Dashboard Payload
    # ═══════════════════════════════════════════════════════════

    def build_dashboard_payload(self) -> dict:
        """
        Construct the complete dashboard data packet from current state.
        Merges simulator data with agent analysis results.
        """
        readings = self.engine.get_recent_readings()
        trend_dir, rate, arrow = self._compute_trend(readings)
        tir = self._compute_tir(readings)

        # Build chart history (last 6 hours of actual readings)
        history = [
            {
                "time": r.timestamp.strftime("%H:%M"),
                "glucose": r.glucose_mg_dl,
                "timestamp": r.timestamp.isoformat()
            }
            for r in readings
        ]

        # Forecast from agent analysis
        forecast = self.latest_analysis.get("forecast_60min", [])

        analysis = self.latest_analysis

        return {
            "type": "glucose_update",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "glucose": readings[-1].glucose_mg_dl if readings else 110.0,
            "trend": trend_dir.value,
            "trend_arrow": arrow,
            "rate_of_change": round(rate, 2),
            "history": history,
            "forecast": forecast,
            "predicted_hypo": analysis.get("predicted_hypo", False),
            "predicted_hyper": analysis.get("predicted_hyper", False),
            "prediction_text": analysis.get("prediction_text", ""),
            "prediction_text_ar": analysis.get("prediction_text_ar", ""),
            "urgency_level": analysis.get("urgency_level", "stable"),
            "dietary_suggestion": analysis.get("dietary_suggestion", ""),
            "dietary_suggestion_ar": analysis.get("dietary_suggestion_ar", ""),
            "activity_suggestion": analysis.get("activity_suggestion", ""),
            "activity_suggestion_ar": analysis.get("activity_suggestion_ar", ""),
            "clinical_reasoning": analysis.get("clinical_reasoning", ""),
            "clinical_reasoning_ar": analysis.get("clinical_reasoning_ar", ""),
            "anomaly_detected": analysis.get("anomaly_detected", False),
            "anomaly_details": analysis.get("anomaly_details", ""),
            "anomaly_details_ar": analysis.get("anomaly_details_ar", ""),
            "iob_units": round(self.engine.get_current_iob(), 2),
            "exercise_active": self.engine.is_exercising(),
            "tir_percent": tir,
        }

    # ═══════════════════════════════════════════════════════════
    #  Main Streaming Loop
    # ═══════════════════════════════════════════════════════════

    async def _run_loop(self) -> None:
        """
        The core streaming loop. Runs continuously until stopped.
        On each tick:
          1. Advance the Bergman engine by one step (5 sim-minutes)
          2. Run the agent pipeline (if registered)
          3. Broadcast the dashboard payload to all WebSocket subscribers
        """
        settings = get_settings()
        logger.info(
            f"🚀 CGM Streamer started — "
            f"interval={settings.SIM_INTERVAL_SEC}s, "
            f"noise_σ={settings.SENSOR_NOISE_STD}, "
            f"ISF_lag={settings.ISF_LAG_MINUTES}min"
        )

        self._is_running = True
        _tick = 0   # Counter to throttle LLM calls

        while self._is_running:
            try:
                # ── Step 1: Advance simulation ──
                reading = self.engine.step()
                self.latest_reading = reading

                # ── Step 2: Run agent pipeline (every 12 ticks = 60s to save API quota) ──
                _tick += 1
                if self._agent_pipeline and _tick % 12 == 1:
                    try:
                        self.latest_analysis = await asyncio.to_thread(
                            self._agent_pipeline,
                            reading,
                            self.engine.get_recent_readings(),
                            self.engine
                        )
                    except Exception as e:
                        logger.error(f"Agent pipeline error: {e}", exc_info=True)

                # ── Step 3: Broadcast to WebSocket subscribers ──
                payload = self.build_dashboard_payload()
                await self._broadcast(payload)

                # ── Step 4: Push live glucose to chat clients ──
                if self._chat_push_callback:
                    try:
                        await self._chat_push_callback(payload)
                    except Exception as e:
                        logger.warning(f"Chat push callback error: {e}")

                # ── Logging ──
                trend_dir, rate, arrow = self._compute_trend(self.engine.get_recent_readings())
                logger.info(
                    f"⏱ Glucose: {reading.glucose_mg_dl} mg/dL {arrow} "
                    f"(rate: {rate:+.1f} mg/dL/min) | "
                    f"IOB: {self.engine.get_current_iob():.1f}u | "
                    f"Exercise: {'🏃' if self.engine.is_exercising() else '—'}"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Streamer loop error: {e}", exc_info=True)

            await asyncio.sleep(settings.SIM_INTERVAL_SEC)

        logger.info("🛑 CGM Streamer stopped")

    # ═══════════════════════════════════════════════════════════
    #  Lifecycle Management
    # ═══════════════════════════════════════════════════════════

    async def start(self) -> None:
        """Start the streaming loop as a background task."""
        if self._is_running:
            logger.warning("Streamer is already running")
            return
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the streaming loop gracefully."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    @property
    def is_running(self) -> bool:
        return self._is_running


# ═══════════════════════════════════════════════════════════════
#  Singleton Instance
# ═══════════════════════════════════════════════════════════════

streamer = CGMStreamer()
