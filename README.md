# DiaSentry — AI Diabetes Management Platform

<div align="center">

![DiaSentry Banner](https://img.shields.io/badge/DiaSentry-AI%20Diabetes%20Platform-blue?style=for-the-badge&logo=heart&logoColor=white)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6B6B?style=flat)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A proactive, real-time AI clinical decision support platform for diabetes management.**  
Built with a LangGraph multi-agent pipeline, Bergman CGM simulation, ADA clinical RAG, and a bilingual Arabic/English AI chatbot.

</div>

---

## 🩺 What is DiaSentry?

DiaSentry replaces reactive diabetes monitoring with a **proactive AI agent system** that:
- **Simulates** a Continuous Glucose Monitor (CGM) using the Bergman Minimal Model (RK4 ODE)
- **Predicts** glucose levels 60 minutes into the future using EWMA forecasting
- **Recommends** personalized clinical actions based on ADA Standards of Care
- **Chats** with the patient in real-time — in Arabic or English

> *"Don't wait for the hypo. DiaSentry warns you before it happens."*

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                    │
│                                                         │
│  ┌──────────┐    ┌─────────────────────────────────┐   │
│  │ Bergman  │───▶│     LangGraph Agent Pipeline     │   │
│  │  Engine  │    │                                  │   │
│  │ (RK4 ODE)│    │  [Ingestion] → [Predictive]      │   │
│  └──────────┘    │      → [Recommendation]          │   │
│                  └─────────────┬───────────────────-┘   │
│                                │                        │
│  ┌──────────┐    ┌─────────────▼──────────────────-┐   │
│  │ChromaDB  │◀───│   RAG: ADA Clinical Guidelines   │   │
│  │ (in-mem) │    └──────────────────────────────────┘   │
│  └──────────┘                                           │
└──────────────────────────┬──────────────────────────────┘
                           │ WebSocket (real-time)
┌──────────────────────────▼──────────────────────────────┐
│               Frontend (React 19 + Vite)                │
│   Live Glucose Gauge │ Predictive Chart │ AI Chatbot    │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔬 **Bergman CGM Engine** | Differential equation model (RK4) simulating realistic glucose dynamics, ISF lag, sensor noise |
| 🤖 **3 AI Agents** | Ingestion (anomaly detection) → Predictive (60-min EWMA forecast) → Recommendation (ADA ReAct loop) |
| 📚 **Clinical RAG** | ChromaDB vector store seeded with ADA Standards of Care for evidence-based recommendations |
| 💬 **Bilingual Chatbot** | Arabic/English conversational agent with live CGM context injection |
| ⚡ **Real-Time Streaming** | WebSocket-based live dashboard — glucose updates every 5 seconds |
| 🍽️ **Meal & Exercise Injection** | Dynamic glucose curve response to carb intake and physical activity |
| 🔌 **Multi-LLM Support** | Works with Qwen, GPT-4o, Gemini, or local Ollama models |

---

## 🛠️ Tech Stack

**Backend**
- `Python 3.11` + `FastAPI` + `Uvicorn`
- `LangGraph` — multi-agent orchestration
- `OpenAI SDK` (OpenAI-compatible — works with any provider)
- `ChromaDB` — in-memory vector store
- `Pydantic Settings` — type-safe configuration

**Frontend**
- `React 19` + `TypeScript` + `Vite`
- `TailwindCSS v4` — glassmorphism UI
- `Recharts` — predictive glucose chart
- `WebSocket` — real-time bidirectional streaming

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- An LLM API key **or** [Ollama](https://ollama.ai) for local inference

### 1. Clone & Configure

```bash
git clone https://github.com/Fadi-Alharbi/DiaSentry.git
cd DiaSentry
cp .env.example .env
# Edit .env with your API key (see options below)
```

### 2. LLM Options (choose one)

```env
# Option A — Local (free, private, no internet needed)
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=qwen2.5:7b

# Option B — Qwen Cloud (DashScope)
OPENAI_API_KEY=sk-ws-your-key-here
OPENAI_BASE_URL=
OPENAI_MODEL=qwen-plus

# Option C — OpenAI
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini
```

### 3. Start the Backend

```bash
pip install -r backend/requirements.txt
python -m backend.main
# → Server running at http://localhost:8000
```

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
# → UI running at http://localhost:5173
```

---

## 🧪 Try It Out

Once running, from the dashboard:

1. **Watch the live glucose gauge** update every 5 seconds
2. **Inject a meal** — add 60g high-GI carbs (e.g., Pizza) and watch the curve spike
3. **Inject exercise** — 30 min intense activity → glucose drops
4. **Chat with the AI** — ask in Arabic or English:
   - *"كيف حال سكري الآن؟"*
   - *"How will pizza affect my glucose?"*
   - *"What should I do before the gym?"*

---

## 📁 Project Structure

```
DiaSentry/
├── backend/
│   ├── agents/
│   │   ├── ingestion_agent.py    # Anomaly detection
│   │   ├── predictive_agent.py   # 60-min EWMA forecast
│   │   ├── recommendation_agent.py # ADA ReAct loop
│   │   ├── chat_agent.py         # Bilingual chatbot
│   │   └── workflow.py           # LangGraph pipeline
│   ├── rag/
│   │   ├── knowledge_base.py     # ChromaDB vector store
│   │   └── ada_guidelines.py     # ADA clinical chunks
│   ├── simulator/
│   │   ├── engine.py             # Bergman RK4 engine
│   │   └── streamer.py           # Async CGM streamer
│   ├── config.py                 # Pydantic settings
│   └── main.py                   # FastAPI app
├── frontend/
│   └── src/
│       ├── components/           # UI components
│       └── hooks/                # WebSocket hooks
├── .env.example
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---


<div align="center">
Built with ❤️ for 463 million people living with diabetes worldwide.
</div>
