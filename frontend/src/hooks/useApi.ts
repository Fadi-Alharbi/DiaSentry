/* ═══════════════════════════════════════════════════════════════
   DiaSentry — useApi Hook
   REST API helpers for meal/activity logging and dashboard polling
   ═══════════════════════════════════════════════════════════════ */

import { useCallback, useState } from "react";
import { API_BASE } from "../lib/constants";

interface UseApiReturn {
  logMeal: (carbs_g: number, glycemic_index: number, food_name: string) => Promise<void>;
  logActivity: (duration_min: number, intensity: number, activity_name: string) => Promise<void>;
  sendChatMessage: (message: string) => Promise<string>;
  isLoading: boolean;
  error: string | null;
}

export function useApi(): UseApiReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const logMeal = useCallback(async (carbs_g: number, glycemic_index: number, food_name: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/log-meal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ carbs_g, glycemic_index, food_name }),
      });
      if (!res.ok) throw new Error("Failed to log meal");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logActivity = useCallback(async (duration_min: number, intensity: number, activity_name: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/log-activity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration_min, intensity, activity_name }),
      });
      if (!res.ok) throw new Error("Failed to log activity");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendChatMessage = useCallback(async (message: string): Promise<string> => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) throw new Error("Chat request failed");
      const data = await res.json();
      return data.response || "No response received.";
    } catch (e) {
      setError((e as Error).message);
      return "Sorry, I couldn't connect to the AI assistant. Please try again.";
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { logMeal, logActivity, sendChatMessage, isLoading, error };
}
