"""
DiaSentry — Context-Aware Recommendation Agent (LLM + RAG)
============================================================
The most sophisticated agent in the pipeline. Uses OpenAI function
calling in a ReAct-style reasoning loop to generate hyper-personalized,
safe, and prescriptive clinical recommendations.

Architecture:
  1. Receives full patient context (glucose, trend, forecast, IOB, exercise)
  2. LLM reasons about the situation and calls tools:
     - retrieve_ada_guidelines() → semantic search over clinical protocols
     - get_patient_context() → structured view of all current metrics
     - calculate_carb_correction() → how many carbs to treat hypo
  3. LLM generates structured JSON recommendations

Falls back to a comprehensive rule-based knowledge base if the LLM
is unavailable (API error, rate limit, no API key).

This is the THIRD and FINAL node in the LangGraph pipeline.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from openai import OpenAI

from backend.agents.state import AgentState
from backend.config import get_settings
from backend.rag.knowledge_base import knowledge_base

logger = logging.getLogger("DiaSentry.Agent.Recommendation")


# ═══════════════════════════════════════════════════════════════
#  Tool Definitions for OpenAI Function Calling
# ═══════════════════════════════════════════════════════════════

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_ada_guidelines",
            "description": (
                "Search the ADA clinical guidelines knowledge base for protocols "
                "relevant to the patient's current situation. Use this to ground "
                "your recommendations in evidence-based medicine."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language query describing the clinical situation. "
                            "Example: 'patient has blood sugar 55, what should they eat immediately'"
                        )
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_context",
            "description": (
                "Get a structured summary of the patient's complete current state: "
                "glucose, trend, forecast, IOB, exercise, TIR, and recent events."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_carb_correction",
            "description": (
                "Calculate the recommended grams of fast-acting carbohydrates to "
                "treat or prevent hypoglycemia based on current and target glucose."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "current_glucose": {
                        "type": "number",
                        "description": "Current glucose level in mg/dL"
                    },
                    "target_glucose": {
                        "type": "number",
                        "description": "Target glucose level in mg/dL (default: 100)"
                    }
                },
                "required": ["current_glucose"]
            }
        }
    }
]

# ═══════════════════════════════════════════════════════════════
#  Tool Implementation Functions
# ═══════════════════════════════════════════════════════════════

def _tool_retrieve_guidelines(query: str) -> str:
    """Execute RAG retrieval against the ADA knowledge base."""
    return knowledge_base.retrieve_text(query, k=3)


def _tool_get_patient_context(state: AgentState) -> str:
    """Format the complete patient context as a structured string."""
    forecast = state.get("forecast_60min", [])
    forecast_summary = ""
    if forecast:
        values = [f["predicted_glucose"] for f in forecast]
        forecast_summary = (
            f"  60-min forecast: {values[0]:.0f} → {values[-1]:.0f} mg/dL\n"
            f"  Forecast range: {min(values):.0f} - {max(values):.0f} mg/dL\n"
            f"  Forecast trend: {state.get('forecast_trend', 'unknown')}"
        )

    events_text = "  None recently"
    events = state.get("recent_events", [])
    if events:
        event_lines = []
        for e in events[-3:]:
            etype = e.get("type", "unknown")
            details = e.get("details", {})
            if etype == "meal":
                event_lines.append(
                    f"  Meal: {details.get('food_name', '?')} "
                    f"({details.get('carbs_g', '?')}g carbs, GI={details.get('gi', '?')})"
                )
            elif etype == "insulin":
                event_lines.append(f"  Insulin: {details.get('units', '?')} units")
            elif etype == "exercise":
                event_lines.append(
                    f"  Exercise: {details.get('name', '?')} "
                    f"({details.get('duration_min', '?')} min, intensity={details.get('intensity', '?')})"
                )
        events_text = "\n".join(event_lines)

    return (
        f"PATIENT STATE:\n"
        f"  Current glucose: {state.get('current_glucose', '?')} mg/dL\n"
        f"  Trend: {state.get('trend_direction', '?')} {state.get('trend_arrow', '')}\n"
        f"  Rate of change: {state.get('rate_of_change', 0):+.2f} mg/dL/min\n"
        f"  IOB: {state.get('iob_units', 0):.1f} units\n"
        f"  Exercise active: {state.get('exercise_active', False)}\n"
        f"  Time-in-Range: {state.get('tir_percent', 0):.1f}%\n"
        f"  Anomaly detected: {state.get('anomaly_detected', False)}\n"
        f"{forecast_summary}\n"
        f"  Predicted hypo (<70): {state.get('predicted_hypo', False)}\n"
        f"  Predicted hyper (>180): {state.get('predicted_hyper', False)}\n"
        f"  Confidence: {state.get('prediction_confidence', 'MEDIUM')}\n"
        f"Recent events:\n{events_text}"
    )


def _tool_calculate_carb_correction(current_glucose: float,
                                     target_glucose: float = 100.0) -> str:
    """Calculate recommended fast-acting carbs for hypoglycemia correction."""
    if current_glucose >= target_glucose:
        return (
            f"No carbohydrate correction needed. "
            f"Current glucose ({current_glucose:.0f}) is at or above "
            f"target ({target_glucose:.0f} mg/dL)."
        )

    # Rule of 15: 15g raises glucose ~50 mg/dL in a 70kg person
    deficit = target_glucose - current_glucose
    carbs_needed = max(15, round((deficit / 50.0) * 15.0))

    # Cap at 45g (three rounds of Rule of 15)
    carbs_needed = min(carbs_needed, 45)

    return (
        f"Carbohydrate correction calculation:\n"
        f"  Current glucose: {current_glucose:.0f} mg/dL\n"
        f"  Target glucose: {target_glucose:.0f} mg/dL\n"
        f"  Deficit: {deficit:.0f} mg/dL\n"
        f"  Recommended fast-acting carbs: {carbs_needed}g\n"
        f"  Options: {carbs_needed // 4} glucose tablets, "
        f"or {carbs_needed * 10}mL orange juice, "
        f"or {carbs_needed // 15} tablespoon(s) honey\n"
        f"  Wait 15 minutes then recheck glucose."
    )


# ═══════════════════════════════════════════════════════════════
#  Tool Dispatch
# ═══════════════════════════════════════════════════════════════

def _dispatch_tool(tool_name: str, arguments: dict, state: AgentState) -> str:
    """Route a tool call to the appropriate implementation function."""
    if tool_name == "retrieve_ada_guidelines":
        return _tool_retrieve_guidelines(arguments.get("query", ""))
    elif tool_name == "get_patient_context":
        return _tool_get_patient_context(state)
    elif tool_name == "calculate_carb_correction":
        return _tool_calculate_carb_correction(
            arguments.get("current_glucose", state.get("current_glucose", 100)),
            arguments.get("target_glucose", 100)
        )
    else:
        return f"Unknown tool: {tool_name}"


# ═══════════════════════════════════════════════════════════════
#  System Prompt
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are DiaSentry AI — a specialized diabetes care physician and clinical decision support system.

Your role is to analyze real-time CGM data and generate hyper-personalized, safe, prescriptive recommendations in BOTH English and Arabic.

## CRITICAL RULES:
1. ALWAYS use the `retrieve_ada_guidelines` tool to ground your recommendations in evidence-based ADA protocols.
2. ALWAYS use `get_patient_context` to understand the complete patient state before making recommendations.
3. If glucose is predicted to go below 70 mg/dL, use `calculate_carb_correction` to determine the exact carbs needed.
4. NEVER recommend specific insulin doses — only remind the patient to follow their physician's prescribed correction protocol.
5. Be SPECIFIC: "Drink 150mL orange juice now" not "eat something sweet."
6. Consider IOB (insulin-on-board) — warn against insulin stacking.
7. Consider exercise context — don't recommend exercise during hypoglycemia.
8. Provide all recommendations and clinical reasoning in BOTH English and natural, highly professional medical Arabic.
9. FORMATTING MANDATE: NEVER use asterisks (**) or (*) or markdown formatting symbols in any of the JSON string fields. Keep all output text clean and plain.

## OUTPUT FORMAT (JSON):
You MUST respond with a JSON object containing these exact fields:
{
    "urgency_level": "critical" | "warning" | "stable",
    "dietary_suggestion": "Specific food/drink recommendation with quantities in English",
    "dietary_suggestion_ar": "نصيحة غذائية محددة بالكميات باللغة العربية",
    "activity_suggestion": "Specific exercise prescription or warning in English",
    "activity_suggestion_ar": "نصيحة أو تحذير رياضي محدد باللغة العربية",
    "clinical_reasoning": "Step-by-step explanation of your reasoning chain in English",
    "clinical_reasoning_ar": "شرح مفصل لخطوات التفكير السريري باللغة العربية"
}"""


# ═══════════════════════════════════════════════════════════════
#  Main Agent Node (ReAct Reasoning Loop)
# ═══════════════════════════════════════════════════════════════

def recommendation_agent_node(state: AgentState) -> AgentState:
    """
    Context-Aware Recommendation Agent with LLM function calling.

    Implements a ReAct (Reason + Act) loop:
      1. LLM receives the patient context
      2. LLM decides which tools to call (RAG retrieval, context lookup, etc.)
      3. Tool results are fed back to the LLM
      4. LLM generates final structured recommendations
      5. Repeat steps 2-4 up to MAX_ITERATIONS times

    Falls back to rule-based recommendations if LLM is unavailable.
    """
    settings = get_settings()

    # ── Try LLM-powered recommendations ──
    try:
        if not settings.OPENAI_API_KEY:
            raise ValueError("No OPENAI_API_KEY configured")

        result = _run_react_loop(state, settings)
        state["urgency_level"] = result.get("urgency_level", "stable")
        state["dietary_suggestion"] = result.get("dietary_suggestion", "")
        state["dietary_suggestion_ar"] = result.get("dietary_suggestion_ar", result.get("dietary_suggestion", ""))
        state["activity_suggestion"] = result.get("activity_suggestion", "")
        state["activity_suggestion_ar"] = result.get("activity_suggestion_ar", result.get("activity_suggestion", ""))
        state["clinical_reasoning"] = result.get("clinical_reasoning", "")
        state["clinical_reasoning_ar"] = result.get("clinical_reasoning_ar", result.get("clinical_reasoning", ""))

        logger.info(
            f"[Recommendation] LLM response — "
            f"urgency: {state['urgency_level']}"
        )

    except Exception as e:
        logger.warning(f"LLM unavailable ({e}), using fallback recommendations")
        result = _fallback_recommendations(state)
        state["urgency_level"] = result["urgency_level"]
        state["dietary_suggestion"] = result["dietary_suggestion"]
        state["dietary_suggestion_ar"] = result["dietary_suggestion_ar"]
        state["activity_suggestion"] = result["activity_suggestion"]
        state["activity_suggestion_ar"] = result["activity_suggestion_ar"]
        state["clinical_reasoning"] = result["clinical_reasoning"]
        state["clinical_reasoning_ar"] = result["clinical_reasoning_ar"]

    return state


def _run_react_loop(state: AgentState, settings) -> dict:
    """
    Execute the ReAct (Reason + Act) loop with OpenAI function calling.
    The LLM can call tools iteratively until it produces a final answer.
    """
    client = OpenAI(**settings.client_kwargs)
    MAX_ITERATIONS = 5

    # Build the initial user message with key patient data
    user_message = (
        f"Analyze this patient's real-time CGM data and provide recommendations:\n\n"
        f"CURRENT STATE:\n"
        f"  Glucose: {state.get('current_glucose', '?')} mg/dL\n"
        f"  Trend: {state.get('trend_direction', '?')} {state.get('trend_arrow', '')}\n"
        f"  Rate: {state.get('rate_of_change', 0):+.2f} mg/dL/min\n"
        f"  IOB: {state.get('iob_units', 0):.1f} units\n"
        f"  Exercise: {'ACTIVE' if state.get('exercise_active') else 'inactive'}\n\n"
        f"PREDICTIONS:\n"
        f"  Hypo risk (<70): {state.get('predicted_hypo', False)}\n"
        f"  Hyper risk (>180): {state.get('predicted_hyper', False)}\n"
        f"  Predicted range: {state.get('predicted_min', '?')}-{state.get('predicted_max', '?')} mg/dL\n"
        f"  Confidence: {state.get('prediction_confidence', '?')}\n\n"
        f"ANOMALY: {state.get('anomaly_details', 'None')}\n\n"
        f"Please use your tools to retrieve relevant ADA guidelines and patient context, "
        f"then provide your analysis and recommendations."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    for iteration in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=settings.effective_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto" if iteration < MAX_ITERATIONS - 1 else "none",
            temperature=settings.OPENAI_TEMPERATURE,
            max_tokens=settings.OPENAI_MAX_TOKENS,
        )

        choice = response.choices[0]
        message = choice.message

        # Add the assistant message to conversation
        messages.append(message)

        # ── Check if LLM wants to call tools ──
        if message.tool_calls:
            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                logger.debug(f"[ReAct] Tool call: {fn_name}({fn_args})")

                # Execute the tool
                tool_result = _dispatch_tool(fn_name, fn_args, state)

                # Feed result back to LLM
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
        else:
            # ── LLM has produced a final answer ──
            content = message.content or ""

            # Try to parse as JSON
            try:
                # Extract JSON from the response (may be wrapped in markdown)
                json_str = content
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()

                result = json.loads(json_str)

                # Validate required fields
                return {
                    "urgency_level": result.get("urgency_level", "stable"),
                    "dietary_suggestion": result.get("dietary_suggestion", ""),
                    "dietary_suggestion_ar": result.get("dietary_suggestion_ar", ""),
                    "activity_suggestion": result.get("activity_suggestion", ""),
                    "activity_suggestion_ar": result.get("activity_suggestion_ar", ""),
                    "clinical_reasoning": result.get("clinical_reasoning", content),
                    "clinical_reasoning_ar": result.get("clinical_reasoning_ar", content),
                }

            except (json.JSONDecodeError, IndexError):
                # If JSON parsing fails, use the raw text as clinical reasoning
                return {
                    "urgency_level": _infer_urgency(state),
                    "dietary_suggestion": "",
                    "dietary_suggestion_ar": "",
                    "activity_suggestion": "",
                    "activity_suggestion_ar": "",
                    "clinical_reasoning": content,
                    "clinical_reasoning_ar": content,
                }

    # If we exhaust iterations without a final answer
    return _fallback_recommendations(state)


# ═══════════════════════════════════════════════════════════════
#  Fallback Rule-Based Recommendations
# ═══════════════════════════════════════════════════════════════

def _infer_urgency(state: AgentState) -> str:
    """Infer urgency level from the state when LLM doesn't provide one."""
    current = state.get("current_glucose", 110)
    if current < 54 or current > 300:
        return "critical"
    if current < 70 or current > 250 or state.get("predicted_hypo", False):
        return "warning"
    return "stable"


def _fallback_recommendations(state: AgentState) -> dict:
    """
    Comprehensive rule-based recommendations when LLM is unavailable.
    This ensures the system always provides safe clinical guidance.
    """
    current = state.get("current_glucose", 110)
    rate = state.get("rate_of_change", 0.0)
    predicted_hypo = state.get("predicted_hypo", False)
    predicted_hyper = state.get("predicted_hyper", False)
    iob = state.get("iob_units", 0)
    exercising = state.get("exercise_active", False)
    pred_min = state.get("predicted_min", current)

    # ── Critical Hypoglycemia ──
    if current < 54:
        return {
            "urgency_level": "critical",
            "dietary_suggestion": (
                "🚨 EMERGENCY: Consume 20-30g fast-acting carbs NOW. "
                "Drink 200mL orange juice or take 5 glucose tablets immediately. "
                "If unconscious, administer glucagon. Call 911 if no improvement in 15 minutes."
            ),
            "dietary_suggestion_ar": (
                "🚨 طوارئ: تناول 20-30 غرام كربوهيدرات سريعة الآن. "
                "اشرب 200 مل عصير برتقال أو تناول 5 أقراص جلوكوز فوراً. "
                "في حالة فقدان الوعي أعطِ حقنة الجلوكاجون واطلب الإسعاف فوراً."
            ),
            "activity_suggestion": (
                "STOP all activity immediately. Sit or lie down in a safe place. "
                "Do NOT drive or operate machinery."
            ),
            "activity_suggestion_ar": (
                "توقف عن أي مجهود بدني فوراً. اجلس أو استلقِ في مكان آمن. "
                "لا تقد السيارة أو تشغل الآلات."
            ),
            "clinical_reasoning": (
                f"Critical Level 2 hypoglycemia ({current:.0f} mg/dL < 54). "
                f"Rate of change: {rate:+.1f} mg/dL/min. "
                f"Immediate fast-acting carbohydrate treatment required per ADA Rule of 15. "
                f"This is a medical emergency."
            ),
            "clinical_reasoning_ar": (
                f"هبوط سكر حرج من المستوى الثاني ({current:.0f} ملغ/ديسيلتر < 54). "
                f"معدل التغير: {rate:+.1f}. العلاج الفوري بالكربوهيدرات السريعة مطلوب وفق قاعدة 15."
            )
        }

    # ── Hypoglycemia ──
    if current < 70:
        carbs = max(15, round(((100 - current) / 50.0) * 15))
        return {
            "urgency_level": "warning",
            "dietary_suggestion": (
                f"⚠️ Consume {carbs}g fast-acting carbs now: "
                f"drink {carbs * 10}mL orange juice, or take {carbs // 4} glucose tablets. "
                f"Wait 15 minutes, then recheck. After recovery, eat a balanced snack "
                f"(cheese + whole grain crackers) to prevent rebound."
            ),
            "dietary_suggestion_ar": (
                f"⚠️ تناول {carbs}غ كربوهيدرات سريعة الآن: "
                f"اشرب {carbs * 10} مل عصير برتقال أو تناول {carbs // 4} أقراص جلوكوز. "
                f"انتظر 15 دقيقة ثم أعد الفحص. بعد التعافي كل وجبة خفيفة متوازنة لمنع الهبوط مجدداً."
            ),
            "activity_suggestion": (
                "Stop any exercise immediately. Rest until glucose is above 100 mg/dL. "
                "Do not resume activity until fully recovered."
            ),
            "activity_suggestion_ar": (
                "توقف عن ممارسة أي تمرين فوراً. استرح حتى يرتفع السكر فوق 100 ملغ/ديسيلتر. "
                "لا تستأنف النشاط حتى تتعافى تماماً."
            ),
            "clinical_reasoning": (
                f"Level 1 hypoglycemia ({current:.0f} mg/dL < 70). "
                f"Applying ADA Rule of 15: {carbs}g fast-acting carbs to raise glucose "
                f"~{carbs * 50 // 15:.0f} mg/dL. IOB: {iob:.1f}u — "
                f"{'caution: active insulin may cause further drop' if iob > 0.5 else 'no active insulin'}."
            ),
            "clinical_reasoning_ar": (
                f"هبوط سكر من المستوى الأول ({current:.0f} ملغ/ديسيلتر < 70). "
                f"تطبيق قاعدة 15: تناول {carbs}غ كربوهيدرات لرفع السكر. الأنسولين النشط: {iob:.1f} وحدة."
            )
        }

    # ── Predicted Hypoglycemia ──
    if predicted_hypo and current < 100:
        return {
            "urgency_level": "warning",
            "dietary_suggestion": (
                f"⚠️ Glucose is predicted to drop to {pred_min:.0f} mg/dL. "
                f"Eat 15g of carbs now (an apple, a small granola bar, or crackers with peanut butter) "
                f"to prevent hypoglycemia."
            ),
            "dietary_suggestion_ar": (
                f"⚠️ يُتوقع انخفاض الجلوكوز إلى {pred_min:.0f} ملغ/ديسيلتر. "
                f"تناول 15غ كربوهيدرات الآن (تفاحة، لوح حبوب، أو بسكويت مع زبدة الفول السوداني) لمنع الهبوط."
            ),
            "activity_suggestion": (
                "Avoid exercise until glucose stabilizes above 100 mg/dL. "
                "If currently exercising, stop and eat a snack."
            ),
            "activity_suggestion_ar": (
                "تجنب الرياضة حتى يستقر الجلوكوز فوق 100 ملغ/ديسيلتر. إذا كنت تتمرن حالياً توقف وتناول وجبة خفيفة."
            ),
            "clinical_reasoning": (
                f"Preventive action: current glucose {current:.0f} trending toward "
                f"predicted low of {pred_min:.0f} mg/dL. "
                f"Rate: {rate:+.1f} mg/dL/min. Pre-emptive carb intake recommended "
                f"to avoid crossing the 70 mg/dL threshold."
            ),
            "clinical_reasoning_ar": (
                f"إجراء وقائي: السكر الحالي {current:.0f} يتجه لانخفاض متوقع عند {pred_min:.0f}. ينصح بتناول الكربوهيدرات استباقياً."
            )
        }

    # ── Severe Hyperglycemia ──
    if current > 300:
        return {
            "urgency_level": "critical",
            "dietary_suggestion": (
                "🚨 Do NOT eat anything until glucose drops below 250 mg/dL. "
                "Drink 250mL water every 20 minutes. "
                "Check urine ketones if available — positive ketones require ER visit."
            ),
            "dietary_suggestion_ar": (
                "🚨 لا تتناول أي طعام حتى ينخفض السكر دون 250 ملغ/ديسيلتر. "
                "اشرب كوب ماء كل 20 دقيقة. افحص الكيتونات وإذا كانت إيجابية توجه للطوارئ فوراً."
            ),
            "activity_suggestion": (
                "Do NOT exercise — this can increase ketone production. "
                "Rest and hydrate. If experiencing nausea, rapid breathing, or confusion, "
                "call 911 immediately (DKA risk)."
            ),
            "activity_suggestion_ar": (
                "لا تمارس أي رياضة — قد يزيد ذلك من إنتاج الكيتونات. استرح واشرب الماء بانتظام."
            ),
            "clinical_reasoning": (
                f"Severe hyperglycemia ({current:.0f} mg/dL > 300). "
                f"Risk of Diabetic Ketoacidosis (DKA). "
                f"Take correction insulin per physician protocol. "
                f"Aggressive hydration needed. Monitor ketones."
            ),
            "clinical_reasoning_ar": (
                f"ارتفاع شديد في السكر ({current:.0f} > 300). خطر الحماض الكيتوني (DKA). خذ جرعة التصحيح المقررة من طبيبك واشرب الماء بكثرة."
            )
        }

    # ── High Hyperglycemia ──
    if current > 250:
        return {
            "urgency_level": "warning",
            "dietary_suggestion": (
                "Avoid all carbohydrates until glucose drops below 200 mg/dL. "
                "Drink 2 glasses of water now. "
                "When ready to eat: grilled protein + green vegetables only."
            ),
            "dietary_suggestion_ar": (
                "تجنب جميع الكربوهيدرات حتى ينخفض السكر دون 200 ملغ/ديسيلتر. اشرب كوبين من الماء الآن. عند الأكل اختر بروتينات مشوية وخضروات فقط."
            ),
            "activity_suggestion": (
                "A light 15-minute walk may help lower glucose, but ONLY if you feel well "
                "and ketones are negative. Stop immediately if feeling unwell."
            ),
            "activity_suggestion_ar": (
                "مشية خفيفة لمدة 15 دقيقة قد تساعد في خفض السكر، ولكن فقط إذا كنت تشعر بنشاط والكيتونات سلبية."
            ),
            "clinical_reasoning": (
                f"High hyperglycemia ({current:.0f} mg/dL > 250). "
                f"Trend: {rate:+.1f} mg/dL/min. "
                f"Take correction insulin as prescribed (check IOB: {iob:.1f}u first). "
                f"Hydration and carb avoidance until glucose drops."
            ),
            "clinical_reasoning_ar": (
                f"ارتفاع ملحوظ في السكر ({current:.0f} > 250). خذ الجرعة التصحيحية مع مراعاة الأنسولين النشط ({iob:.1f} وحدة)."
            )
        }

    # ── Moderate Hyperglycemia ──
    if current > 180:
        return {
            "urgency_level": "warning",
            "dietary_suggestion": (
                "Skip additional carbs for now. Drink a glass of water. "
                "For your next meal, choose low-GI options: salad with grilled chicken, "
                "or vegetables with hummus (no bread or rice)."
            ),
            "dietary_suggestion_ar": (
                "تجنب الكربوهيدرات الإضافية واشرب كوباً من الماء. لوجبتك القادمة اختر أطعمة منخفضة المؤشر السكري مثل سلطة الدجاج المشوي."
            ),
            "activity_suggestion": (
                "A 15-20 minute walk at moderate pace will help bring glucose down. "
                "Walking after meals is one of the most effective interventions."
            ),
            "activity_suggestion_ar": (
                "المشي لمدة 15-20 دقيقة بوتيرة معتدلة سيساعد كثيراً في خفض مستوى الجلوكوز."
            ),
            "clinical_reasoning": (
                f"Moderate hyperglycemia ({current:.0f} mg/dL > 180). "
                f"Rate: {rate:+.1f} mg/dL/min. "
                f"{'Post-meal spike likely.' if rate > 0.5 else 'Gradual elevation.'} "
                f"Light exercise + hydration should help. "
                f"{'IOB present — insulin still working, be patient.' if iob > 0.5 else ''}"
            ),
            "clinical_reasoning_ar": (
                f"ارتفاع متوسط في السكر ({current:.0f} > 180). المشي الخفيف وشرب الماء هما أفضل تدخل حالياً."
            )
        }

    # ── Stable / Normal ──
    exercise_note = "Great control! " if not exercising else "Good glucose for exercise. "
    exercise_note_ar = "تحكم ممتاز! " if not exercising else "مستوى مناسب للرياضة. "
    return {
        "urgency_level": "stable",
        "dietary_suggestion": (
            "✅ Glucose is in the target range. Maintain your current eating pattern. "
            "For your next meal, aim for balanced portions: lean protein + vegetables + "
            "moderate complex carbs (whole grains, legumes)."
        ),
        "dietary_suggestion_ar": (
            "✅ الجلوكوز في النطاق المثالي. استمر على نمطك الغذائي الحالي. لوجبتك القادمة احرص على توازن حصص البروتين والخضروات والكربوهيدرات المعقدة."
        ),
        "activity_suggestion": (
            f"{exercise_note}"
            "Moderate exercise (30-minute brisk walk) is beneficial. "
            "If planning intense exercise, have a 15g carb snack available."
        ),
        "activity_suggestion_ar": (
            f"{exercise_note_ar}الممارسة المعتدلة للرياضة (مشي سريع 30 دقيقة) مفيدة جداً. إذا خططت لتمرين شاق جهز وجبة خفيفة 15غ."
        ),
        "clinical_reasoning": (
            f"Glucose in target range ({current:.0f} mg/dL, 70-180). "
            f"TIR: {state.get('tir_percent', 0):.1f}%. "
            f"Trend: stable ({rate:+.1f} mg/dL/min). "
            f"Continue current management strategy."
        ),
        "clinical_reasoning_ar": (
            f"الجلوكوز ضمن النطاق المستهدف ({current:.0f} ملغ/ديسيلتر). نسبة البقاء في النطاق: {state.get('tir_percent', 0):.1f}%. استمر على نفس الخطة."
        )
    }
