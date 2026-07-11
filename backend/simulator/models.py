"""
DiaSentry — Simulator Data Models
===================================
Pydantic models for all simulator data types: events, readings, and state.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ═══════════════════════════════════════════════════════════════
#  Enumerations
# ═══════════════════════════════════════════════════════════════

class TrendDirection(str, Enum):
    """CGM-standard trend arrow classifications based on rate of change."""
    RAPIDLY_RISING = "RAPIDLY_RISING"       # > +3 mg/dL/min  ↑↑
    RISING = "RISING"                       # +2 to +3        ↑
    SLIGHTLY_RISING = "SLIGHTLY_RISING"     # +1 to +2        ↗
    STABLE = "STABLE"                       # -1 to +1        →
    SLIGHTLY_FALLING = "SLIGHTLY_FALLING"   # -2 to -1        ↘
    FALLING = "FALLING"                     # -3 to -2        ↓
    RAPIDLY_FALLING = "RAPIDLY_FALLING"     # < -3            ↓↓


class UrgencyLevel(str, Enum):
    """Urgency classification for AI recommendations."""
    CRITICAL = "critical"
    WARNING = "warning"
    STABLE = "stable"


# ═══════════════════════════════════════════════════════════════
#  Event Models — Inputs from the User
# ═══════════════════════════════════════════════════════════════

class MealEvent(BaseModel):
    """A meal event logged by the user via /api/log-meal."""
    carbs_g: float = Field(..., gt=0, description="Grams of carbohydrates")
    glycemic_index: float = Field(
        default=55.0, ge=1, le=100,
        description="Glycemic Index (1-100). Low=35, Medium=55, High=70+"
    )
    food_name: Optional[str] = Field(default=None, description="Name of the food item")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())


class ActivityEvent(BaseModel):
    """An exercise event logged by the user via /api/log-activity."""
    duration_min: float = Field(..., gt=0, description="Duration in minutes")
    intensity: float = Field(
        default=1.0, ge=0.1, le=3.0,
        description="Intensity multiplier (0.1=light walking, 1.0=moderate, 2.0=intense, 3.0=extreme)"
    )
    activity_name: Optional[str] = Field(default=None, description="Name/type of activity")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())


# ═══════════════════════════════════════════════════════════════
#  Glucose Reading — Output from the Simulator
# ═══════════════════════════════════════════════════════════════

class GlucoseReading(BaseModel):
    """A single CGM glucose reading with metadata."""
    timestamp: datetime
    glucose_mg_dl: float = Field(..., ge=30.0, le=500.0, description="Interstitial glucose in mg/dL")
    blood_glucose_mg_dl: float = Field(..., ge=30.0, le=500.0, description="True blood glucose (hidden from user)")
    is_noisy: bool = Field(default=True, description="Whether sensor noise was applied")


# ═══════════════════════════════════════════════════════════════
#  Simulator Internal State
# ═══════════════════════════════════════════════════════════════

class SimulatorState(BaseModel):
    """
    Internal state of the Bergman Minimal Model at a point in time.
    G = plasma glucose, X = insulin action compartment, I = plasma insulin.
    """
    G: float = Field(default=110.0, description="Plasma glucose (mg/dL)")
    X: float = Field(default=0.0, description="Insulin action state variable (1/min)")
    I: float = Field(default=10.0, description="Plasma insulin (μU/mL)")
    G_isf: float = Field(default=110.0, description="Interstitial fluid glucose (mg/dL) — lagged")
    time_min: float = Field(default=0.0, description="Simulation time in minutes")

    # Active gut absorption rate (Ra) — accumulator from all active meals
    Ra: float = Field(default=0.0, description="Current gut glucose absorption rate (mg/dL/min)")

    # Active exercise glucose utilization rate
    exercise_rate: float = Field(default=0.0, description="Exercise-driven glucose utilization (mg/dL/min)")


# ═══════════════════════════════════════════════════════════════
#  Dashboard Data — Sent to Frontend
# ═══════════════════════════════════════════════════════════════

class DashboardPayload(BaseModel):
    """Complete payload sent to the frontend via WebSocket on each reading."""
    # Core metrics
    timestamp: str
    glucose: float
    trend: str
    trend_arrow: str
    rate_of_change: float

    # History for chart
    history: List[dict] = Field(default_factory=list, description="Last 6 hours of readings")
    forecast: List[dict] = Field(default_factory=list, description="Next 60-min forecast points")

    # Predictions
    predicted_hypo: bool = False
    predicted_hyper: bool = False
    prediction_text: str = ""

    # AI Recommendations
    urgency_level: str = "stable"
    dietary_suggestion: str = ""
    activity_suggestion: str = ""
    clinical_reasoning: str = ""

    # Anomaly
    anomaly_detected: bool = False
    anomaly_details: str = ""

    # IOB & Exercise context
    iob_units: float = 0.0
    exercise_active: bool = False

    # Time in Range
    tir_percent: float = 0.0


# ═══════════════════════════════════════════════════════════════
#  Chat Models
# ═══════════════════════════════════════════════════════════════

class ChatMessage(BaseModel):
    """A single chat message in the conversational AI."""
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""
    message: str = Field(..., min_length=1, description="User message text")
