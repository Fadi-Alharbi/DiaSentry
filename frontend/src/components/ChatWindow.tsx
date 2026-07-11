import React, { useState, useEffect, useRef } from "react";
import { Send, Bot, User, Sparkles, Activity } from "lucide-react";
import { CHAT_WS_URL } from "../lib/constants";
import type { ChatMessage } from "../lib/types";

interface ChatWindowProps {
  lang?: "en" | "ar";
}

interface LiveGlucose {
  glucose: number | string;
  trend_arrow: string;
  rate_of_change: number;
  urgency_level: string;
  predicted_hypo: boolean;
  predicted_hyper: boolean;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ lang = "ar" }) => {
  const isAr = lang === "ar";
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: isAr
        ? "مرحباً! أنا مساعد DiaSentry الذكي 🩺\nأراقب مستوى سكرك لحظياً وسأجيب على أسئلتك بالعربية أو الإنجليزية.\nاسألني عن وضعك الآن، أو عن تأثير وجبة، أو أي شيء عن مرض السكري."
        : "Welcome to DiaSentry AI! I monitor your glucose in real-time. Ask me about your current status, food impact, or anything about diabetes management.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [liveGlucose, setLiveGlucose] = useState<LiveGlucose | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(CHAT_WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setIsConnected(true);
      ws.onclose = () => {
        setIsConnected(false);
        setTimeout(connect, 3000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // ── Live glucose push from sensor (every 5s) ────────────────
          if (data.type === "glucose_update") {
            setLiveGlucose({
              glucose: data.glucose,
              trend_arrow: data.trend_arrow ?? "→",
              rate_of_change: data.rate_of_change ?? 0,
              urgency_level: data.urgency_level ?? "stable",
              predicted_hypo: data.predicted_hypo ?? false,
              predicted_hyper: data.predicted_hyper ?? false,
            });
            return;
          }

          // ── Typing indicator while AI is thinking ───────────────────
          if (data.type === "typing") {
            setIsTyping(data.is_typing === true);
            return;
          }

          // ── Full AI response from local qwen2.5:7b ──────────────────
          if (data.type === "chat_response" && data.response) {
            setIsTyping(false);
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: data.response,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              },
            ]);
          }
        } catch (e) {
          console.error(e);
        }
      };
    };

    connect();
    return () => wsRef.current?.close();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    const userMsg: ChatMessage = {
      role: "user",
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    wsRef.current.send(JSON.stringify({ message: input }));
    setInput("");
  };

  // Glucose badge color based on clinical status
  const glucoseBadgeColor = liveGlucose
    ? liveGlucose.predicted_hypo
      ? "bg-red-500/20 text-red-300 border-red-500/40"
      : liveGlucose.predicted_hyper
      ? "bg-orange-500/20 text-orange-300 border-orange-500/40"
      : "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
    : "bg-slate-700/40 text-slate-400 border-slate-600/40";

  return (
    <div className="flex flex-col h-[400px] bg-slate-900/60 backdrop-blur-xl border border-slate-800 rounded-3xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 bg-slate-950/40 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center shadow-lg">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
              <span>{isAr ? "المساعد السريري بالذكاء الاصطناعي" : "DiaSentry Clinical AI"}</span>
              <Sparkles className="w-3 h-3 text-purple-400" />
            </h4>
            <span className="text-[10px] text-slate-400 flex items-center gap-1">
              <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
              <span>
                {isConnected
                  ? isAr ? "متصل • qwen2.5:7b محلي" : "Connected • Local qwen2.5:7b"
                  : isAr ? "جاري الاتصال..." : "Connecting..."}
              </span>
            </span>
          </div>
        </div>

        {/* Live glucose badge — updated automatically on every sensor tick */}
        {liveGlucose && (
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-[11px] font-bold transition-all duration-500 ${glucoseBadgeColor}`}>
            <Activity className="w-3 h-3" />
            <span>{liveGlucose.glucose} mg/dL</span>
            <span className="opacity-80">{liveGlucose.trend_arrow}</span>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3 space-y-1">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex items-start gap-2.5 max-w-[85%] ${
              msg.role === "user" ? "self-end flex-row-reverse" : "self-start"
            }`}
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                msg.role === "user" ? "bg-emerald-600" : "bg-slate-800 border border-slate-700"
              }`}
            >
              {msg.role === "user" ? (
                <User className="w-3.5 h-3.5 text-white" />
              ) : (
                <Bot className="w-3.5 h-3.5 text-purple-400" />
              )}
            </div>

            <div
              className={`p-3.5 rounded-2xl text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-gradient-to-tr from-emerald-600 to-teal-600 text-white rounded-tr-none shadow-md"
                  : "bg-slate-950/70 border border-slate-800/80 text-slate-200 rounded-tl-none shadow-md"
              }`}
              style={{ direction: /[\u0600-\u06FF]/.test(msg.content) ? "rtl" : "ltr" }}
            >
              <p className="whitespace-pre-wrap font-medium">{msg.content.replace(/[\*]/g, "")}</p>
              <span className={`text-[9px] block mt-1.5 opacity-60 ${msg.role === "user" ? "text-right" : "text-left"}`}>
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {/* Animated typing indicator while AI is processing */}
        {isTyping && (
          <div className="flex items-start gap-2.5 max-w-[85%] self-start">
            <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 bg-slate-800 border border-slate-700">
              <Bot className="w-3.5 h-3.5 text-purple-400" />
            </div>
            <div className="p-3.5 rounded-2xl rounded-tl-none bg-slate-950/70 border border-slate-800/80 shadow-md">
              <div className="flex items-center gap-1">
                <span
                  className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce"
                  style={{ animationDelay: "0ms" }}
                />
                <span
                  className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce"
                  style={{ animationDelay: "150ms" }}
                />
                <span
                  className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce"
                  style={{ animationDelay: "300ms" }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="p-3 bg-slate-950/60 border-t border-slate-800/80 flex items-center gap-2">
        <input
          type="text"
          placeholder={
            isAr
              ? "اسأل الذكاء الاصطناعي... (مثال: كيف حال سكري الآن؟)"
              : "Ask AI anything (e.g. how is my glucose now?)"
          }
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 bg-slate-900/80 border border-slate-800 rounded-2xl px-4 py-2.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-purple-500"
          dir="auto"
        />
        <button
          type="submit"
          disabled={!input.trim() || !isConnected}
          className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-40 flex items-center justify-center text-white transition-all shadow-lg shrink-0"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
