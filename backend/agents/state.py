"""
DiaSentry — LangGraph Agent State Schema
==========================================
Defines the TypedDict shared state that flows through the
multi-agent pipeline: Ingestion → Predictive → Recommendation.
"""

from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """
    Shared state flowing through the LangGraph agent pipeline.
    Each agent reads and writes to this state dictionary.
    """

    # ═══════════════════════════════════════════════════════════
    #  Inputs (populated by the streamer before pipeline runs)
    # ═══════════════════════════════════════════════════════════

    # Current glucose reading from the simulator
    current_glucose: float
    current_timestamp: str

    # Historical readings buffer (last 72 readings = 6 hours)
    history_buffer: List[Dict[str, Any]]

    # Active events context
    recent_events: List[Dict[str, Any]]
    iob_units: float
    exercise_active: bool

    # ═══════════════════════════════════════════════════════════
    #  Ingestion & Anomaly Agent Outputs
    # ═══════════════════════════════════════════════════════════

    # Trend analysis
    trend_direction: str           # TrendDirection enum value
    trend_arrow: str               # Arrow symbol (↑, →, ↓, etc.)
    rate_of_change: float          # mg/dL per minute

    # Anomaly detection
    anomaly_detected: bool
    anomaly_details: str

    # Time-in-Range
    tir_percent: float

    # ═══════════════════════════════════════════════════════════
    #  Predictive Agent Outputs
    # ═══════════════════════════════════════════════════════════

    # 60-minute forecast (12 x 5-min predicted values)
    forecast_60min: List[Dict[str, Any]]
    forecast_trend: str            # "rising", "falling", "stable"

    # Threshold breach predictions
    predicted_hypo: bool           # Any forecast point < 70 mg/dL
    predicted_hyper: bool          # Any forecast point > 180 mg/dL
    predicted_min: float           # Lowest forecasted value
    predicted_max: float           # Highest forecasted value

    # Prediction confidence
    prediction_confidence: str     # "HIGH", "MEDIUM", "LOW"
    prediction_text: str           # Human-readable prediction narrative (English)
    prediction_text_ar: str        # Human-readable prediction narrative (Arabic)

    # ═══════════════════════════════════════════════════════════
    #  Recommendation Agent Outputs (LLM-generated)
    # ═══════════════════════════════════════════════════════════

    urgency_level: str             # "critical", "warning", "stable"
    dietary_suggestion: str        # What to eat/drink (English)
    dietary_suggestion_ar: str     # What to eat/drink (Arabic)
    activity_suggestion: str       # Exercise prescription (English)
    activity_suggestion_ar: str    # Exercise prescription (Arabic)
    clinical_reasoning: str        # Step-by-step AI reasoning chain (English)
    clinical_reasoning_ar: str     # Step-by-step AI reasoning chain (Arabic)
    anomaly_details_ar: str        # Anomaly details in Arabic
