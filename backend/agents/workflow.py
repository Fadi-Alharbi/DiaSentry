"""
DiaSentry — LangGraph Workflow Definition
============================================
Defines the multi-agent pipeline as a LangGraph StateGraph:

  IngestionAgent → PredictiveAgent → RecommendationAgent → END

The Ingestion Agent feeds validated data + anomaly flags to the
Predictive Agent, which forecasts the glucose curve. The Recommendation
Agent then uses LLM + RAG to generate prescriptive actions.
"""

import logging
from typing import List, Dict, Any

from langgraph.graph import StateGraph, END

from backend.agents.state import AgentState
from backend.agents.ingestion_agent import ingestion_agent_node
from backend.agents.predictive_agent import predictive_agent_node
from backend.agents.recommendation_agent import recommendation_agent_node

logger = logging.getLogger("DiaSentry.Agent.Workflow")


def build_workflow() -> StateGraph:
    """
    Construct the LangGraph multi-agent pipeline.

    Pipeline:
        IngestionAgent → PredictiveAgent → RecommendationAgent → END

    The graph is compiled into a runnable that accepts an AgentState
    dict and returns the enriched state with all agent outputs.
    """
    workflow = StateGraph(AgentState)

    # ── Add nodes ──
    workflow.add_node("IngestionAgent", ingestion_agent_node)
    workflow.add_node("PredictiveAgent", predictive_agent_node)
    workflow.add_node("RecommendationAgent", recommendation_agent_node)

    # ── Define edges (sequential pipeline) ──
    workflow.add_edge("IngestionAgent", "PredictiveAgent")
    workflow.add_edge("PredictiveAgent", "RecommendationAgent")
    workflow.add_edge("RecommendationAgent", END)

    # ── Set entry point ──
    workflow.set_entry_point("IngestionAgent")

    logger.info("LangGraph workflow built: Ingestion → Predictive → Recommendation")

    return workflow.compile()


# ═══════════════════════════════════════════════════════════════
#  Pipeline Runner
# ═══════════════════════════════════════════════════════════════

# Compile the workflow once at module load
agent_pipeline = build_workflow()


def run_agent_pipeline(reading, history: list, engine) -> dict:
    """
    Execute the full agent pipeline for a single glucose reading.

    This is the callback function passed to the CGM streamer.
    It constructs the initial AgentState from the reading + engine state,
    runs the LangGraph workflow, and returns the enriched state dict.

    Args:
        reading: GlucoseReading from the simulator
        history: List of recent GlucoseReading objects
        engine: Reference to the BergmanEngine for IOB/exercise queries

    Returns:
        dict: The complete AgentState with all agent outputs
    """
    # Build history buffer in dict format for the state
    history_buffer = [
        {
            "glucose": r.glucose_mg_dl,
            "glucose_mg_dl": r.glucose_mg_dl,
            "timestamp": r.timestamp.isoformat(),
            "time": r.timestamp.strftime("%H:%M")
        }
        for r in history[-72:]   # Last 6 hours
    ]

    # Get recent events from engine
    recent_events = engine.get_recent_events(within_minutes=30.0)

    # Construct initial state
    initial_state: AgentState = {
        # Inputs
        "current_glucose": reading.glucose_mg_dl,
        "current_timestamp": reading.timestamp.isoformat(),
        "history_buffer": history_buffer,
        "recent_events": recent_events,
        "iob_units": engine.get_current_iob(),
        "exercise_active": engine.is_exercising(),

        # Ingestion outputs (to be filled)
        "trend_direction": "STABLE",
        "trend_arrow": "→",
        "rate_of_change": 0.0,
        "anomaly_detected": False,
        "anomaly_details": "",
        "tir_percent": 0.0,

        # Predictive outputs (to be filled)
        "forecast_60min": [],
        "forecast_trend": "stable",
        "predicted_hypo": False,
        "predicted_hyper": False,
        "predicted_min": reading.glucose_mg_dl,
        "predicted_max": reading.glucose_mg_dl,
        "prediction_confidence": "LOW",
        "prediction_text": "",

        # Recommendation outputs (to be filled)
        "urgency_level": "stable",
        "dietary_suggestion": "",
        "activity_suggestion": "",
        "clinical_reasoning": "",
    }

    try:
        # Run the LangGraph pipeline
        final_state = agent_pipeline.invoke(initial_state)
        return final_state
    except Exception as e:
        logger.error(f"Pipeline execution error: {e}", exc_info=True)
        return initial_state
