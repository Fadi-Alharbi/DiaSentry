
"""
DiaSentry — Ingestion & Anomaly Detection Agent
=================================================
Continually monitors the virtual sensor stream:
  • Validates incoming data
  • Computes rate-of-change and trend classification
  • Detects unexplained anomalies (>2 mg/dL/min without logged events)
  • Calculates Time-in-Range

This is the FIRST node in the LangGraph pipeline.
"""

import logging
from typing import List, Dict, Any

from backend.agents.state import AgentState
from backend.config import get_settings

logger = logging.getLogger("DiaSentry.Agent.Ingestion")


def ingestion_agent_node(state: AgentState) -> AgentState:
    """
    Ingestion & Anomaly Detection Agent.

    Reads: current_glucose, history_buffer, recent_events
    Writes: trend_direction, trend_arrow, rate_of_change,
            anomaly_detected, anomaly_details, tir_percent
    """
    settings = get_settings()
    current = state["current_glucose"]
    history = state.get("history_buffer", [])

    # ═══════════════════════════════════════════════════════════
    #  1. Data Validation
    # ═══════════════════════════════════════════════════════════

    if current < 30.0 or current > 500.0:
        logger.warning(f"Glucose reading out of physiological range: {current}")
        current = max(30.0, min(current, 500.0))
        state["current_glucose"] = current

    # ═══════════════════════════════════════════════════════════
    #  2. Rate of Change Calculation
    # ═══════════════════════════════════════════════════════════

    rate = 0.0
    if len(history) >= 2:
        # Use weighted average of last 3 readings for smoothness
        recent = history[-min(4, len(history)):]
        rates = []

        for i, reading in enumerate(recent):
            glucose_val = reading.get("glucose", reading.get("glucose_mg_dl", current))
            steps_back = len(recent) - i
            time_delta = steps_back * 5.0  # Each reading is 5 minutes apart
            if time_delta > 0:
                r = (current - glucose_val) / time_delta
                weight = i + 1
                rates.append((r, weight))

        if rates:
            rate = sum(r * w for r, w in rates) / sum(w for _, w in rates)

    state["rate_of_change"] = round(rate, 2)

    # ═══════════════════════════════════════════════════════════
    #  3. Trend Classification (CGM Standard)
    # ═══════════════════════════════════════════════════════════

    if rate > 3.0:
        trend, arrow = "RAPIDLY_RISING", "↑↑"
    elif rate > 2.0:
        trend, arrow = "RISING", "↑"
    elif rate > 1.0:
        trend, arrow = "SLIGHTLY_RISING", "↗"
    elif rate > -1.0:
        trend, arrow = "STABLE", "→"
    elif rate > -2.0:
        trend, arrow = "SLIGHTLY_FALLING", "↘"
    elif rate > -3.0:
        trend, arrow = "FALLING", "↓"
    else:
        trend, arrow = "RAPIDLY_FALLING", "↓↓"

    state["trend_direction"] = trend
    state["trend_arrow"] = arrow

    # ═══════════════════════════════════════════════════════════
    #  4. Anomaly Detection
    # ═══════════════════════════════════════════════════════════
    #  If glucose is changing > ANOMALY_RATE mg/dL/min AND
    #  no meal, insulin, or exercise event was logged in the last 30 min,
    #  flag as "unexplained anomaly".

    anomaly = False
    anomaly_details = ""
    anomaly_details_ar = ""

    if abs(rate) > settings.ANOMALY_RATE:
        recent_events = state.get("recent_events", [])
        has_explanation = len(recent_events) > 0

        if not has_explanation:
            anomaly = True
            direction = "rising" if rate > 0 else "falling"
            direction_ar = "يرتفع" if rate > 0 else "ينخفض"
            anomaly_details = (
                f"⚠️ UNEXPLAINED ANOMALY: Glucose is {direction} at "
                f"{abs(rate):.1f} mg/dL/min with no logged meal, insulin, "
                f"or exercise event in the last 30 minutes. "
                f"This could indicate sensor error, stress, illness, or "
                f"missed event logging. Verify with fingerstick if possible."
            )
            anomaly_details_ar = (
                f"⚠️ شذوذ غير مبرر في الحركية: السكر {direction_ar} بسرعة "
                f"{abs(rate):.1f} ملغ/ديسيلتر بالدقيقة دون وجود أي وجبة أو جرعة أنسولين أو تمرين "
                f"مسجل في آخر 30 دقيقة. قد يشير ذلك إلى خطأ في المستشعر، إجهاد، مرض، أو "
                f"نسيان تسجيل حدث. يُنصح بالتأكد عبر فحص الأصبع إن أمكن."
            )
            logger.warning(
                f"[Anomaly] Unexplained rapid glucose change: "
                f"{rate:+.1f} mg/dL/min at glucose={current}"
            )

    state["anomaly_detected"] = anomaly
    state["anomaly_details"] = anomaly_details
    state["anomaly_details_ar"] = anomaly_details_ar

    # ═══════════════════════════════════════════════════════════
    #  5. Time-in-Range Calculation
    # ═══════════════════════════════════════════════════════════

    if history:
        glucose_values = [
            h.get("glucose", h.get("glucose_mg_dl", 0))
            for h in history
        ]
        glucose_values.append(current)
        in_range = sum(
            1 for v in glucose_values
            if settings.TARGET_LOW <= v <= settings.TARGET_HIGH
        )
        tir = round((in_range / len(glucose_values)) * 100, 1)
    else:
        tir = 100.0 if settings.TARGET_LOW <= current <= settings.TARGET_HIGH else 0.0

    state["tir_percent"] = tir

    logger.info(
        f"[Ingestion] Glucose: {current} {arrow} "
        f"(rate: {rate:+.2f}) | TIR: {tir}% | "
        f"Anomaly: {'YES' if anomaly else 'no'}"
    )

    return state
