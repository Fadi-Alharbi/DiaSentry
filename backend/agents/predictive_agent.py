"""
DiaSentry — Time-Series Predictive Agent
==========================================
Uses the last 12 readings (60 minutes) to forecast the glucose curve
for the next 60 minutes (t+60 horizon) at 5-minute intervals.

Employs Exponentially Weighted Moving Average (EWMA) with:
  • Momentum (acceleration tracking)
  • Physiological damping (increasing with horizon)
  • Mean-reversion toward euglycemia (~110 mg/dL)
  • Confidence scoring based on data stability

This is the SECOND node in the LangGraph pipeline.
"""

import math
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta

from backend.agents.state import AgentState
from backend.config import get_settings

logger = logging.getLogger("DiaSentry.Agent.Predictive")


def predictive_agent_node(state: AgentState) -> AgentState:
    """
    Time-Series Predictive Agent.

    Reads: current_glucose, history_buffer, rate_of_change, trend_direction,
           recent_events, anomaly_detected
    Writes: forecast_60min, forecast_trend, predicted_hypo, predicted_hyper,
            predicted_min, predicted_max, prediction_confidence, prediction_text
    """
    settings = get_settings()
    current = state["current_glucose"]
    history = state.get("history_buffer", [])
    rate = state.get("rate_of_change", 0.0)
    trend = state.get("trend_direction", "STABLE")

    # ═══════════════════════════════════════════════════════════
    #  1. Extract Recent Values
    # ═══════════════════════════════════════════════════════════

    # Get the last 12 glucose values (60 min of 5-min readings)
    recent_values = []
    for h in history[-12:]:
        val = h.get("glucose", h.get("glucose_mg_dl", None))
        if val is not None:
            recent_values.append(float(val))
    recent_values.append(current)

    # ═══════════════════════════════════════════════════════════
    #  2. EWMA Baseline
    # ═══════════════════════════════════════════════════════════

    alpha = 0.3  # EWMA smoothing factor

    if len(recent_values) >= 3:
        ewma = recent_values[0]
        for val in recent_values[1:]:
            ewma = alpha * val + (1 - alpha) * ewma
    else:
        ewma = current

    # ═══════════════════════════════════════════════════════════
    #  3. Momentum (Acceleration)
    # ═══════════════════════════════════════════════════════════

    acceleration = 0.0
    if len(recent_values) >= 4:
        # Velocity at t-1
        prev_rate = (recent_values[-2] - recent_values[-3]) / 5.0
        # Acceleration = change in velocity
        acceleration = (rate - prev_rate) / 5.0

    # ═══════════════════════════════════════════════════════════
    #  4. Generate 60-Minute Forecast (12 x 5-min steps)
    # ═══════════════════════════════════════════════════════════

    forecast_points = []
    mean_reversion_target = 110.0  # Physiological equilibrium
    reversion_strength = 0.015     # How strongly glucose pulls toward normal

    now = datetime.now(timezone.utc)

    for step in range(1, settings.PREDICTION_STEPS + 1):
        t = step * 5.0  # Minutes ahead

        # ── Damping factor ──
        # Increases with horizon: predictions further out are less confident
        # and glucose dynamics naturally dampen
        damping = max(0.15, 1.0 - (t / 120.0))

        # ── Base prediction ──
        # EWMA extrapolation with damped velocity and momentum
        pred = (ewma
                + rate * t * damping
                + 0.5 * acceleration * t * t * 0.003 * damping)

        # ── Mean reversion ──
        # Glucose tends to return toward euglycemia over time
        reversion = (mean_reversion_target - pred) * reversion_strength * step
        pred += reversion

        # ── Account for known active events ──
        events = state.get("recent_events", [])
        for event in events:
            event_type = event.get("type", "")
            if event_type == "meal":
                carbs = event.get("details", {}).get("carbs_g", 50)
                # Meals cause a rise peaking at ~45 min post-meal
                meal_effect = (carbs / 15.0) * math.sin(math.pi * min(t, 90) / 90.0)
                if t < 120:
                    pred += meal_effect * damping

            elif event_type == "exercise":
                intensity = event.get("details", {}).get("intensity", 1.0)
                # Exercise lowers glucose
                pred -= 1.5 * intensity * damping * min(t / 30.0, 1.0)

        # ── Physiological bounds ──
        pred = max(40.0, min(pred, 450.0))

        forecast_time = now + timedelta(minutes=t)
        forecast_points.append({
            "time": forecast_time.strftime("%H:%M"),
            "minutes_ahead": int(t),
            "predicted_glucose": round(pred, 1),
            "timestamp": forecast_time.isoformat()
        })

    state["forecast_60min"] = forecast_points

    # ═══════════════════════════════════════════════════════════
    #  5. Threshold Breach Detection
    # ═══════════════════════════════════════════════════════════

    predicted_values = [fp["predicted_glucose"] for fp in forecast_points]
    pred_min = min(predicted_values) if predicted_values else current
    pred_max = max(predicted_values) if predicted_values else current

    state["predicted_min"] = pred_min
    state["predicted_max"] = pred_max
    state["predicted_hypo"] = pred_min < settings.HYPO_THRESHOLD
    state["predicted_hyper"] = pred_max > settings.HYPER_THRESHOLD

    # Forecast overall trend
    if len(predicted_values) >= 2:
        net_change = predicted_values[-1] - predicted_values[0]
        if net_change > 10:
            state["forecast_trend"] = "rising"
        elif net_change < -10:
            state["forecast_trend"] = "falling"
        else:
            state["forecast_trend"] = "stable"
    else:
        state["forecast_trend"] = "stable"

    # ═══════════════════════════════════════════════════════════
    #  6. Confidence Scoring
    # ═══════════════════════════════════════════════════════════

    if abs(rate) < 0.5 and len(recent_values) >= 8:
        confidence = "HIGH"
    elif abs(rate) < 1.5 and len(recent_values) >= 4:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Reduce confidence if anomaly detected
    if state.get("anomaly_detected", False):
        confidence = "LOW"

    state["prediction_confidence"] = confidence

    # ═══════════════════════════════════════════════════════════
    #  7. Prediction Narrative
    # ═══════════════════════════════════════════════════════════

    narrative = _build_prediction_narrative(
        current, pred_min, pred_max, predicted_values,
        state["forecast_trend"], rate, confidence,
        state.get("predicted_hypo", False),
        state.get("predicted_hyper", False),
        state.get("recent_events", [])
    )
    narrative_ar = _build_prediction_narrative_ar(
        current, pred_min, pred_max, predicted_values,
        state["forecast_trend"], rate, confidence,
        state.get("predicted_hypo", False),
        state.get("predicted_hyper", False),
        state.get("recent_events", [])
    )
    state["prediction_text"] = narrative
    state["prediction_text_ar"] = narrative_ar

    logger.info(
        f"[Predictive] Forecast: {pred_min:.0f}-{pred_max:.0f} mg/dL | "
        f"Trend: {state['forecast_trend']} | Confidence: {confidence} | "
        f"Hypo: {state['predicted_hypo']} | Hyper: {state['predicted_hyper']}"
    )

    return state


# ═══════════════════════════════════════════════════════════════
#  Narrative Builder
# ═══════════════════════════════════════════════════════════════

def _build_prediction_narrative(
    current: float, pred_min: float, pred_max: float,
    predicted_values: List[float],
    forecast_trend: str, rate: float, confidence: str,
    hypo_risk: bool, hyper_risk: bool,
    recent_events: List[dict]
) -> str:
    """Build a human-readable prediction narrative."""

    parts = []
    parts.append(f"Current glucose: {current:.0f} mg/dL")

    # Direction
    if forecast_trend == "rising":
        parts.append(
            f"Prediction: Glucose is expected to RISE over the next 60 minutes, "
            f"reaching up to {pred_max:.0f} mg/dL."
        )
    elif forecast_trend == "falling":
        parts.append(
            f"Prediction: Glucose is expected to DROP over the next 60 minutes, "
            f"potentially reaching {pred_min:.0f} mg/dL."
        )
    else:
        parts.append(
            f"Prediction: Glucose is expected to remain STABLE around "
            f"{predicted_values[-1]:.0f} mg/dL over the next 60 minutes."
        )

    # Threshold warnings
    if hypo_risk:
        hypo_val = pred_min
        # Find when it crosses 70
        for i, v in enumerate(predicted_values):
            if v < 70:
                minutes = (i + 1) * 5
                parts.append(
                    f"⚠️ HYPOGLYCEMIA RISK: Expected drop to {hypo_val:.0f} mg/dL "
                    f"within {minutes} minutes. Act NOW to prevent low blood sugar."
                )
                break

    if hyper_risk:
        hyper_val = pred_max
        for i, v in enumerate(predicted_values):
            if v > 180:
                minutes = (i + 1) * 5
                parts.append(
                    f"⚠️ HYPERGLYCEMIA RISK: Expected rise to {hyper_val:.0f} mg/dL "
                    f"within {minutes} minutes."
                )
                break

    # Event context
    if recent_events:
        event_names = []
        for e in recent_events[-2:]:
            etype = e.get("type", "")
            details = e.get("details", {})
            if etype == "meal":
                food = details.get("food_name", details.get("name", "meal"))
                carbs = details.get("carbs_g", "?")
                event_names.append(f"{food} ({carbs}g carbs)")
            elif etype == "exercise":
                name = details.get("name", "exercise")
                event_names.append(name)
            elif etype == "insulin":
                units = details.get("units", "?")
                event_names.append(f"insulin ({units} units)")

        if event_names:
            parts.append(f"Contributing factors: {', '.join(event_names)}")

    parts.append(f"Prediction confidence: {confidence}")

    return " | ".join(parts)


def _build_prediction_narrative_ar(
    current: float, pred_min: float, pred_max: float,
    predicted_values: List[float],
    forecast_trend: str, rate: float, confidence: str,
    hypo_risk: bool, hyper_risk: bool,
    recent_events: List[dict]
) -> str:
    """Build an Arabic human-readable prediction narrative."""

    conf_ar = {"HIGH": "عالية", "MEDIUM": "متوسطة", "LOW": "منخفضة"}.get(confidence, "متوسطة")
    parts = []
    parts.append(f"السكر الحالي: {current:.0f} ملغ/ديسيلتر")

    # Direction
    if forecast_trend == "rising":
        parts.append(
            f"التوقعات: يُتوقع ارتفاع الجلوكوز خلال الـ 60 دقيقة القادمة، "
            f"لحدود {pred_max:.0f} ملغ/ديسيلتر."
        )
    elif forecast_trend == "falling":
        parts.append(
            f"التوقعات: يُتوقع انخفاض الجلوكوز خلال الـ 60 دقيقة القادمة، "
            f"لحدود {pred_min:.0f} ملغ/ديسيلتر."
        )
    else:
        parts.append(
            f"التوقعات: يُتوقع استقرار الجلوكوز حول "
            f"{predicted_values[-1]:.0f} ملغ/ديسيلتر خلال الـ 60 دقيقة القادمة."
        )

    # Threshold warnings
    if hypo_risk:
        hypo_val = pred_min
        for i, v in enumerate(predicted_values):
            if v < 70:
                minutes = (i + 1) * 5
                parts.append(
                    f"⚠️ خطر هبوط السكر: يُتوقع الانخفاض إلى {hypo_val:.0f} ملغ/ديسيلتر "
                    f"خلال {minutes} دقيقة. تصرف فوراً لتجنب الهبوط."
                )
                break

    if hyper_risk:
        hyper_val = pred_max
        for i, v in enumerate(predicted_values):
            if v > 180:
                minutes = (i + 1) * 5
                parts.append(
                    f"⚠️ تحذير ارتفاع السكر: يُتوقع الارتفاع إلى {hyper_val:.0f} ملغ/ديسيلتر "
                    f"خلال {minutes} دقيقة."
                )
                break

    # Event context
    if recent_events:
        event_names = []
        for e in recent_events[-2:]:
            etype = e.get("type", "")
            details = e.get("details", {})
            if etype == "meal":
                food = details.get("food_name", details.get("name", "وجبة"))
                carbs = details.get("carbs_g", "?")
                event_names.append(f"{food} ({carbs}غ كربوهيدرات)")
            elif etype == "exercise":
                name = details.get("name", "تمرين")
                event_names.append(name)
            elif etype == "insulin":
                units = details.get("units", "?")
                event_names.append(f"أنسولين ({units} وحدات)")

        if event_names:
            parts.append(f"العوامل المؤثرة: {', '.join(event_names)}")

    parts.append(f"دقة التوقعات: {conf_ar}")

    return " | ".join(parts)
