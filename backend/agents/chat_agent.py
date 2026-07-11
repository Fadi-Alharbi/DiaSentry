"""
DiaSentry — Conversational AI Chat Agent
==========================================
Handles natural-language queries from the patient via the chat interface.
Supports Arabic and English. Has access to the same tools as the
Recommendation Agent (RAG retrieval, patient context, carb calculation)
plus a meal parsing tool for natural language food logging.

Maintains conversation memory (last N messages) for contextual dialogue.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from openai import OpenAI
from backend.simulator.streamer import streamer as _cgm_streamer

from backend.config import get_settings
from backend.rag.knowledge_base import knowledge_base

logger = logging.getLogger("DiaSentry.Agent.Chat")


# ═══════════════════════════════════════════════════════════════
#  Tool Definitions for Chat Agent
# ═══════════════════════════════════════════════════════════════

CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "retrieve_ada_guidelines",
            "description": "Search ADA clinical guidelines for relevant protocols.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Clinical query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_context",
            "description": "Get the patient's complete current state (glucose, trend, forecast, IOB, etc.).",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_meal_impact",
            "description": (
                "Estimate the glucose impact of a food item described in natural language. "
                "Parse the food into carbs, GI, and predicted glucose rise."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "food_description": {
                        "type": "string",
                        "description": "Natural language food description (e.g., 'a large pepperoni pizza', '2 slices of bread with cheese')"
                    }
                },
                "required": ["food_description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_carb_correction",
            "description": "Calculate fast-acting carbs needed to treat or prevent hypoglycemia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_glucose": {"type": "number"},
                    "target_glucose": {"type": "number"}
                },
                "required": ["current_glucose"]
            }
        }
    }
]


# ═══════════════════════════════════════════════════════════════
#  Chat System Prompt
# ═══════════════════════════════════════════════════════════════

CHAT_SYSTEM_PROMPT = """You are DiaSentry AI Assistant — a friendly, knowledgeable diabetes care companion.

You speak naturally in whatever language the patient uses (Arabic or English).
You have real-time access to the patient's CGM data and can provide personalized advice.

## YOUR CAPABILITIES:
1. Answer questions about diabetes management, food, exercise, and medications.
2. Estimate the glucose impact of foods the patient wants to eat.
3. Provide personalized recommendations based on their LIVE glucose data.
4. Retrieve ADA clinical guidelines when needed.
5. Help patients understand their glucose patterns and trends.

## CRITICAL RULES:
1. ALWAYS use `get_patient_context` to know the patient's current state before answering.
2. Be warm, supportive, and encouraging — never judgmental.
3. For food questions, use `estimate_meal_impact` to give specific carb/GI estimates.
4. NEVER recommend specific insulin doses — refer to their physician.
5. If the patient seems to be in a dangerous state (hypo/hyper), prioritize safety advice.
6. Be SPECIFIC and actionable — "eat 15g carbs" not "eat something."
7. LANGUAGE MANDATE: Check the user's input language carefully. If the user writes in Arabic (e.g., "ماهي حالتي", "كيف السكر"), your ENTIRE response MUST be in natural, fluent Arabic. DO NOT respond in English if the query is in Arabic.
8. FORMATTING MANDATE: NEVER use asterisks (**) or (*) or markdown formatting like (# or _). Write clean, beautifully formatted plain text using neat paragraphs, clear line breaks, and emojis or symbols like (• or 🔸).

## EXAMPLE INTERACTIONS:
Patient: "I'm going to the gym now, what should I do?"
You: [Check context first] "Your glucose is currently 110 mg/dL and stable — great for exercise! Have a small snack (a banana or granola bar, ~15g carbs) before starting. Keep glucose tablets handy and check your levels after 30 minutes."

Patient: "ماهي حالتي الآن؟" (What is my status right now?)
You: [Check context first] "مستوى سكر الدم الحالي لديك هو 110 ملغ/ديسيلتر وهو في حالة استقرار ممتازة ضمن النطاق المستهدف! التوقعات للساعة القادمة تشير إلى استمرار الاستقرار. هل لديك استفسار عن وجبة أو تمرين معين؟"

Patient: "كيف ستأثر البيتزا على سكري؟" (How will pizza affect my sugar?)
You: [Estimate meal] "البيتزا (شريحتين) تحتوي تقريباً 60-80 غرام كربوهيدرات بمؤشر سكري مرتفع (~70). مع سكرك الحالي 135، متوقع يرتفع السكر إلى حوالي 200-220 بعد ساعة. نصيحتي: كل شريحة واحدة مع سلطة خضار، وامشِ 15 دقيقة بعد الأكل."
"""


class ChatAgent:
    """
    Conversational AI assistant with memory and tool access.

    Maintains a conversation history buffer and uses OpenAI function
    calling to provide contextual, personalized responses.
    """

    def __init__(self):
        self._conversation_history: List[Dict[str, str]] = []
        self._patient_context: Dict[str, Any] = {}

    def update_context(self, dashboard_data: dict) -> None:
        """Update the patient context with the latest dashboard data (kept for compatibility)."""
        self._patient_context = dashboard_data

    def _get_live_context(self) -> dict:
        """
        Fetches the absolute latest glucose value directly from the raw sensor.
        Priority order:
          1. streamer.latest_reading — the last raw BergmanEngine output (most accurate)
          2. build_dashboard_payload() — full computed payload as fallback
          3. cached _patient_context — last resort
        """
        try:
            # ── PRIMARY: read directly from the raw sensor object ──────────────
            # This is the exact same number displayed on the CGM gauge in the UI.
            if _cgm_streamer.latest_reading is not None:
                r = _cgm_streamer.latest_reading
                # Compute trend & rate from the full payload for context
                payload = _cgm_streamer.build_dashboard_payload()
                return {
                    **payload,
                    # Override glucose with the raw reading to guarantee accuracy
                    "glucose": round(r.glucose_mg_dl, 1),
                    "raw_timestamp": r.timestamp.isoformat(),
                }
        except Exception:
            pass

        try:
            live = _cgm_streamer.build_dashboard_payload()
            if live:
                return live
        except Exception:
            pass

        return self._patient_context

    def _build_live_context_block(self) -> str:
        """
        Build a real-time patient status block injected directly into the system prompt.
        This ensures qwen2.5 (and any small model) always sees the latest sensor reading
        without needing to call get_patient_context as a tool.
        """
        ctx = self._get_live_context()
        if not ctx or ctx.get('glucose') is None:
            return ""

        glucose    = ctx.get('glucose', '?')
        trend      = ctx.get('trend', 'stable')
        arrow      = ctx.get('trend_arrow', '→')
        rate       = ctx.get('rate_of_change', 0.0)
        tir        = ctx.get('tir_percent', 0.0)
        hypo       = ctx.get('predicted_hypo', False)
        hyper      = ctx.get('predicted_hyper', False)
        urgency    = ctx.get('urgency_level', 'stable')
        iob        = ctx.get('iob_units', 0.0)
        exercise   = ctx.get('exercise_active', False)
        updated_at = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')

        # Urgency label
        if hypo or urgency == 'critical':
            status_label = '🔴 CRITICAL — Hypoglycemia Risk'
        elif hyper and glucose > 250:
            status_label = '🔴 CRITICAL — Severe Hyperglycemia'
        elif hyper:
            status_label = '🟡 WARNING — Hyperglycemia'
        elif urgency == 'warning':
            status_label = '🟡 WARNING'
        else:
            status_label = '🟢 IN RANGE'

        return (
            f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📡 LIVE CGM SENSOR — Raw reading at {updated_at}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  ⚡ CURRENT GLUCOSE : {glucose} mg/dL  {arrow}\n"
            f"  Rate of change    : {rate:+.1f} mg/dL/min\n"
            f"  Clinical status   : {status_label}\n"
            f"  Hypo risk (<70)   : {'YES ⚠️' if hypo else 'No'}\n"
            f"  Hyper risk (>180) : {'YES ⚠️' if hyper else 'No'}\n"
            f"  Time-in-Range     : {tir:.1f}%\n"
            f"  Insulin on board  : {iob:.1f} units\n"
            f"  Exercise active   : {'Yes 🏃' if exercise else 'No'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️  CRITICAL RULE: The glucose value is EXACTLY {glucose} mg/dL right now.\n"
            f"   NEVER guess or use a different number. This is the live sensor reading.\n"
            f"   When patient asks about glucose in ANY language, state: {glucose} mg/dL.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    async def process_message(self, user_message: str) -> str:
        """
        Process a user message and generate a contextual AI response.

        Args:
            user_message: The patient's chat message (Arabic or English)

        Returns:
            The AI assistant's response text
        """
        settings = get_settings()

        # Add user message to history
        self._conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Trim history to configured size
        if len(self._conversation_history) > settings.CHAT_MEMORY_SIZE * 2:
            self._conversation_history = self._conversation_history[-settings.CHAT_MEMORY_SIZE * 2:]

        try:
            if not settings.OPENAI_API_KEY:
                raise ValueError("No API key")

            response = await self._run_chat_loop(user_message, settings)

        except Exception as e:
            logger.warning(f"Chat LLM error: {e}")
            response = self._fallback_response(user_message)

        # Add assistant response to history
        self._conversation_history.append({
            "role": "assistant",
            "content": response
        })

        return response

    async def _run_chat_loop(self, user_message: str, settings) -> str:
        """Execute the chat function-calling loop."""
        import asyncio

        client = OpenAI(**settings.client_kwargs)
        # ── Reduced to 2 iterations for much faster responses ─────────────────
        MAX_ITERATIONS = 2

        # ── Inject live CGM data into BOTH the system prompt AND the user msg ──
        # Injecting into the user message ensures small local models (qwen2.5)
        # always see the exact current glucose reading first — regardless of
        # how they process the system prompt.
        live_block = self._build_live_context_block()
        enriched_system_prompt = CHAT_SYSTEM_PROMPT + live_block

        # Build a prefixed user message so the model can never miss the reading
        ctx = self._get_live_context()
        glucose_val = ctx.get('glucose', '?') if ctx else '?'
        trend_arrow = ctx.get('trend_arrow', '→') if ctx else '→'
        rate = ctx.get('rate_of_change', 0.0) if ctx else 0.0
        urgency = ctx.get('urgency_level', 'stable') if ctx else 'stable'

        glucose_prefix = (
            f"[SENSOR READING — RIGHT NOW: Glucose = {glucose_val} mg/dL "
            f"{trend_arrow} | Rate = {rate:+.1f} mg/dL/min | Status = {urgency}]\n\n"
        )
        prefixed_user_message = glucose_prefix + user_message

        # Build messages: system prompt + history (all previous turns) +
        # the current user message WITH the glucose prefix
        history_without_last = self._conversation_history[:-1]  # exclude the just-appended user msg
        messages = [
            {"role": "system", "content": enriched_system_prompt}
        ]
        messages.extend(history_without_last)
        messages.append({"role": "user", "content": prefixed_user_message})

        for iteration in range(MAX_ITERATIONS):
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=settings.effective_model,
                messages=messages,
                tools=CHAT_TOOLS,
                tool_choice="auto" if iteration < MAX_ITERATIONS - 1 else "none",
                temperature=0.3,
                max_tokens=600,
            )

            choice = response.choices[0]
            message = choice.message
            messages.append(message)

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)

                    result = self._dispatch_tool(fn_name, fn_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
            else:
                return message.content or "I'm sorry, I couldn't generate a response."

        return "I apologize, I'm having trouble processing that. Could you rephrase?"

    def _dispatch_tool(self, tool_name: str, arguments: dict) -> str:
        """Route tool calls for the chat agent."""
        if tool_name == "retrieve_ada_guidelines":
            return knowledge_base.retrieve_text(arguments.get("query", ""), k=2)

        elif tool_name == "get_patient_context":
            # Always fetch the LIVE reading directly from the streamer
            ctx = self._get_live_context()
            if not ctx or ctx.get('glucose') is None:
                return "No patient context available yet. Waiting for sensor data."
            glucose = ctx.get('glucose', '?')
            trend = ctx.get('trend', '?')
            arrow = ctx.get('trend_arrow', '')
            rate = ctx.get('rate_of_change', 0)
            iob = ctx.get('iob_units', 0)
            exercise = ctx.get('exercise_active', False)
            tir = ctx.get('tir_percent', 0)
            hypo = ctx.get('predicted_hypo', False)
            hyper = ctx.get('predicted_hyper', False)
            urgency = ctx.get('urgency_level', 'stable')
            fetched_at = datetime.now(timezone.utc).strftime("%H:%M:%S")
            return (
                f"LIVE PATIENT STATE (fetched at {fetched_at} UTC):\n"
                f"  Glucose: {glucose} mg/dL\n"
                f"  Trend: {trend} {arrow}\n"
                f"  Rate: {rate:+.2f} mg/dL/min\n"
                f"  IOB: {iob:.1f} units\n"
                f"  Exercise: {'active' if exercise else 'inactive'}\n"
                f"  TIR: {tir:.1f}%\n"
                f"  Predicted hypo: {hypo}\n"
                f"  Predicted hyper: {hyper}\n"
                f"  Urgency: {urgency}"
            )

        elif tool_name == "estimate_meal_impact":
            food = arguments.get("food_description", "unknown food")
            # Provide common food estimates for the LLM to reason about
            return (
                f"MEAL ESTIMATION for '{food}':\n"
                f"Note: These are approximate estimates. Actual impact varies by individual.\n\n"
                f"Common food database (per typical serving):\n"
                f"  Pizza (1 large slice): ~35g carbs, GI=70, expected rise: +40-60 mg/dL\n"
                f"  Rice (1 cup white): ~45g carbs, GI=73, expected rise: +50-70 mg/dL\n"
                f"  Rice (1 cup brown): ~45g carbs, GI=55, expected rise: +35-50 mg/dL\n"
                f"  Bread (1 slice white): ~15g carbs, GI=75, expected rise: +20-30 mg/dL\n"
                f"  Banana (medium): ~27g carbs, GI=51, expected rise: +25-35 mg/dL\n"
                f"  Apple (medium): ~25g carbs, GI=36, expected rise: +15-25 mg/dL\n"
                f"  Orange juice (250mL): ~26g carbs, GI=50, expected rise: +30-45 mg/dL\n"
                f"  Burger (with bun): ~30g carbs, GI=60, expected rise: +35-50 mg/dL\n"
                f"  Pasta (1 cup): ~43g carbs, GI=50, expected rise: +40-55 mg/dL\n"
                f"  Hummus + pita: ~30g carbs, GI=55, expected rise: +25-35 mg/dL\n"
                f"  Dates (3 pieces): ~36g carbs, GI=103, expected rise: +45-65 mg/dL\n"
                f"  Chicken salad (no bread): ~5g carbs, GI=15, expected rise: +5-10 mg/dL\n\n"
                f"Use these as reference points to estimate '{food}'."
            )

        elif tool_name == "calculate_carb_correction":
            current = arguments.get("current_glucose", 100)
            target = arguments.get("target_glucose", 100)
            if current >= target:
                return f"No correction needed (glucose {current} >= target {target})."
            deficit = target - current
            carbs = max(15, round((deficit / 50) * 15))
            return f"Correction: {carbs}g fast-acting carbs needed to raise from {current} to {target} mg/dL."

        return f"Unknown tool: {tool_name}"

    def _fallback_response(self, user_message: str) -> str:
        """Simple fallback when LLM is unavailable."""
        msg_lower = user_message.lower()
        is_arabic = any('\u0600' <= c <= '\u06FF' for c in user_message)

        # Always use the live reading even in fallback mode
        ctx = self._get_live_context()
        glucose = ctx.get("glucose", "unknown")

        if is_arabic:
            if any(w in user_message for w in ["أكل", "وجبة", "طعام", "غداء", "عشاء", "فطور", "بيتزا"]):
                return (
                    f"مستوى سكر الدم الحالي لديك هو {glucose} ملغ/ديسيلتر. "
                    f"لوجبتك القادمة، أنصحك بحصص متوازنة: بروتين تشبع + خضار + كربوهيدرات معقدة باعتدال. "
                    f"تجنب الأطعمة ذات المؤشر السكري المرتفع مثل الخبز الأبيض والمشروبات الغازية، ويُفضل المشي 15 دقيقة بعد الأكل."
                )

            if any(w in user_message for w in ["رياضة", "مشي", "تمارين", "تمرين", "جري", "جيم"]):
                if isinstance(glucose, (int, float)) and glucose < 100:
                    return (
                        f"⚠️ مستوى الجلوكوز لديك حالياً {glucose} ملغ/ديسيلتر — وهو منخفض للبدء بالتمرين. "
                        f"تناول وجبة خفيفة تحتوي على 15-30غ كربوهيدرات أولاً وانتظر حتى يرتفع السكر فوق 100 ملغ/ديسيلتر."
                    )
                return (
                    f"مستوى الجلوكوز لديك حالياً {glucose} ملغ/ديسيلتر. "
                    f"وضعك آمن وممتاز للقيام بنشاط بدني معتدل! احتفظ بوجبة خفيفة أو أقراص جلوكوز في متناول يدك وافحص السكر بعد 30 دقيقة."
                )

            if any(w in user_message for w in ["منخفض", "هبوط", "دوخة", "انخفاض"]):
                return (
                    "إذا كنت تشعر بهبوط السكر، اتبع قاعدة 15 السريرية فوراً: تناول 15 غراماً من الكربوهيدرات سريعة الامتصاص "
                    "(4 أقراص جلوكوز أو نصف كوب عصير برتقال)، انتظر 15 دقيقة، ثم أعد فحص السكر."
                )

            # Default Arabic fallback (handles "ماهي حالتي", "كيف السكر", etc.)
            return (
                f"مستوى سكر الدم الحالي لديك هو {glucose} ملغ/ديسيلتر وهو يتم متابعته لحظياً عبر محرك Bergman الحركي. "
                f"أنا هنا لمساعدتك والإجابة عن أي استفسارات تخص نظامك الغذائي، أو تمارينك الرياضية، أو حركية السكر لديك. كيف يمكنني مساعدتك؟"
            )

        # English fallbacks
        if any(w in msg_lower for w in ["eat", "food", "meal"]):
            return (
                f"Your current glucose is {glucose} mg/dL. "
                f"For your next meal, I recommend balanced portions: lean protein + "
                f"vegetables + moderate complex carbs. Avoid high-GI foods like white bread "
                f"and sugary drinks. Walk for 10-15 minutes after eating."
            )

        if any(w in msg_lower for w in ["exercise", "gym", "walk", "run"]):
            if isinstance(glucose, (int, float)) and glucose < 100:
                return (
                    f"⚠️ Your glucose is {glucose} mg/dL — too low for exercise. "
                    f"Eat a 15-30g carb snack first and wait until glucose is above 100."
                )
            return (
                f"Your glucose is {glucose} mg/dL. "
                f"Safe for moderate exercise! Have a snack ready and check glucose every 30 minutes."
            )

        if any(w in msg_lower for w in ["low", "hypo"]):
            return (
                "If your blood sugar is low, follow the Rule of 15: eat 15g of fast-acting carbs "
                "(4 glucose tablets or half a cup of orange juice), wait 15 minutes, and recheck."
            )

        return (
            f"Your current glucose is {glucose} mg/dL. "
            f"I'm here to help with any questions about diet, exercise, or glucose management. "
            f"What would you like to know?"
        )

    def clear_history(self) -> None:
        """Reset conversation history."""
        self._conversation_history = []


# Singleton
chat_agent = ChatAgent()
