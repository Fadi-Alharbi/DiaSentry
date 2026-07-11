"""
DiaSentry — Virtual CGM Sensor Engine (Bergman Minimal Model)
==============================================================
A physiological simulation engine that generates realistic interstitial
fluid glucose readings using a simplified Bergman Minimal Model.

The model tracks three state variables via coupled ODEs:
  G(t) — Plasma glucose concentration (mg/dL)
  X(t) — Insulin action in the remote compartment (1/min)
  I(t) — Plasma insulin concentration (μU/mL)

Additional physiological realism:
  • Gut Glucose Absorption Ra(t) — Double-exponential meal model with GI
  • Insulin-on-Board IOB(t) — Exponential decay of injected insulin
  • Exercise Effect — Intensity-driven glucose utilization
  • Interstitial Fluid Lag — First-order 12-minute lag filter
  • Sensor Noise — Gaussian white noise (σ = 2.5 mg/dL)
  • Circadian Rhythm — Dawn phenomenon sinusoidal overlay

References:
  Bergman, R.N., Ider, Y.Z., Bowden, C.R., Cobelli, C. (1979).
  "Quantitative estimation of insulin sensitivity."
  American Journal of Physiology, 236(6), E667-E677.
"""

import math
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from collections import deque

from backend.config import get_settings
from backend.simulator.models import (
    GlucoseReading, SimulatorState, MealEvent, ActivityEvent
)

logger = logging.getLogger("DiaSentry.Simulator.Engine")


# ═══════════════════════════════════════════════════════════════
#  Internal Event Trackers
# ═══════════════════════════════════════════════════════════════

class ActiveMeal:
    """
    Tracks a single active meal's gut absorption kinetics.
    Uses a double-exponential model parameterized by carbs and GI.
    Ra(t) = D * k * (exp(-k_a1*t) - exp(-k_a2*t)) / (k_a2 - k_a1)
    where D = total glucose dose, k = absorption constants scaled by GI.
    """
    def __init__(self, carbs_g: float, glycemic_index: float, start_time: float):
        self.carbs_g = carbs_g
        self.gi = glycemic_index
        self.start_time = start_time

        # Total glucose dose: ~1 mg/dL per gram of carbs for a 70kg person
        # with ~15L glucose distribution volume
        self.dose = carbs_g * 1000.0 / 150.0   # mg/dL equivalent

        # Absorption rate constants scaled by GI
        # Higher GI → faster absorption (larger k values)
        gi_factor = glycemic_index / 50.0       # Normalized around medium GI
        self.k_a1 = 0.012 * gi_factor           # Gastric emptying rate
        self.k_a2 = 0.025 * gi_factor           # Intestinal absorption rate

        # Total expected duration (minutes) — 95% absorbed
        self.duration_min = max(60, 180 / gi_factor)

    def get_ra(self, current_time: float) -> float:
        """
        Calculate gut glucose absorption rate Ra at the given simulation time.
        Returns mg/dL/min.
        """
        t = current_time - self.start_time
        if t < 0 or t > self.duration_min:
            return 0.0

        # Double-exponential absorption curve
        k_diff = self.k_a2 - self.k_a1
        if abs(k_diff) < 1e-8:
            return 0.0

        ra = (self.dose * self.k_a2 *
              (math.exp(-self.k_a1 * t) - math.exp(-self.k_a2 * t)) / k_diff)

        return max(0.0, ra)

    def is_expired(self, current_time: float) -> bool:
        """Check if this meal's absorption is complete."""
        return (current_time - self.start_time) > self.duration_min


class ActiveInsulin:
    """
    Tracks insulin-on-board (IOB) using exponential decay.
    Models the pharmacokinetic profile of rapid-acting insulin.
    """
    def __init__(self, units: float, start_time: float, dia_hours: float = 4.0):
        self.units = units
        self.start_time = start_time
        self.dia_min = dia_hours * 60.0         # Duration of Insulin Action
        self.peak_min = 75.0                     # Time to peak action (minutes)

        # Decay constant based on DIA
        self.k_decay = 3.0 / self.dia_min       # ~95% gone by DIA

    def get_insulin_rate(self, current_time: float) -> float:
        """
        Calculate the insulin action rate at the given time.
        Uses a gamma-like curve: rapid rise to peak, then exponential decay.
        Returns μU/mL/min equivalent.
        """
        t = current_time - self.start_time
        if t < 0 or t > self.dia_min:
            return 0.0

        # Gamma-like curve: t * exp(-k*t)
        normalized_t = t / self.peak_min
        action = (self.units * 8.0 * normalized_t *
                  math.exp(1.0 - normalized_t) * self.k_decay)

        return max(0.0, action)

    def get_iob(self, current_time: float) -> float:
        """Calculate remaining insulin-on-board (units)."""
        t = current_time - self.start_time
        if t < 0:
            return self.units
        if t > self.dia_min:
            return 0.0

        # Exponential decay of IOB
        remaining_fraction = math.exp(-self.k_decay * t)
        return self.units * remaining_fraction

    def is_expired(self, current_time: float) -> bool:
        """Check if this insulin dose is fully absorbed."""
        return (current_time - self.start_time) > self.dia_min


class ActiveExercise:
    """Tracks an active exercise session's glucose-lowering effect."""
    def __init__(self, duration_min: float, intensity: float, start_time: float):
        self.duration_min = duration_min
        self.intensity = intensity
        self.start_time = start_time

        # Post-exercise insulin sensitivity boost lasts 2x the duration
        self.total_effect_min = duration_min * 2.0

    def get_exercise_rate(self, current_time: float) -> float:
        """
        Calculate exercise-driven glucose utilization rate.
        During exercise: direct glucose uptake by muscles.
        After exercise: enhanced insulin sensitivity (lingering effect).
        Returns mg/dL/min of glucose consumed.
        """
        t = current_time - self.start_time
        if t < 0 or t > self.total_effect_min:
            return 0.0

        if t <= self.duration_min:
            # During exercise: direct glucose consumption
            # ~1-3 mg/dL/min depending on intensity
            return 1.5 * self.intensity
        else:
            # Post-exercise: decaying sensitivity boost
            post_t = t - self.duration_min
            decay = math.exp(-0.02 * post_t)
            return 0.5 * self.intensity * decay

    def is_active(self, current_time: float) -> bool:
        """Check if exercise is currently happening (not just lingering effect)."""
        t = current_time - self.start_time
        return 0 <= t <= self.duration_min

    def is_expired(self, current_time: float) -> bool:
        """Check if all exercise effects have worn off."""
        return (current_time - self.start_time) > self.total_effect_min


# ═══════════════════════════════════════════════════════════════
#  Bergman Minimal Model Engine
# ═══════════════════════════════════════════════════════════════

class BergmanEngine:
    """
    Virtual CGM Sensor engine implementing a simplified Bergman Minimal Model.

    Produces clinically realistic glucose trajectories that respond to:
      • Carbohydrate meals (parameterized by grams + Glycemic Index)
      • Insulin doses (with pharmacokinetic IOB decay)
      • Exercise (intensity-driven glucose utilization)
      • Circadian rhythm (dawn phenomenon)
      • Interstitial fluid time lag (12 minutes)
      • Sensor noise (Gaussian, σ = 2.5 mg/dL)

    Usage:
        engine = BergmanEngine()
        engine.inject_meal(carbs_g=60, glycemic_index=70)
        reading = engine.step()   # Advances by 5 simulated minutes
    """

    def __init__(self):
        settings = get_settings()

        # ── Bergman ODE parameters ──
        self.p1 = settings.BERGMAN_P1       # Glucose effectiveness
        self.p2 = settings.BERGMAN_P2       # Insulin action decay
        self.p3 = settings.BERGMAN_P3       # Insulin sensitivity
        self.Gb = settings.BERGMAN_GB       # Basal glucose
        self.Ib = settings.BERGMAN_IB       # Basal insulin
        self.n = settings.BERGMAN_N         # Insulin clearance

        # ── Sensor parameters ──
        self.noise_std = settings.SENSOR_NOISE_STD
        self.isf_lag_min = settings.ISF_LAG_MINUTES
        self.dt = settings.SIM_INTERNAL_STEP_MIN        # ODE step size (1 min)
        self.steps_per_output = settings.SIM_READINGS_PER_OUTPUT

        # ── State variables ──
        self.state = SimulatorState(
            G=self.Gb,
            X=0.0,
            I=self.Ib,
            G_isf=self.Gb,
            time_min=0.0
        )

        # ── ISF lag buffer (circular buffer of blood glucose values) ──
        lag_buffer_size = max(1, int(self.isf_lag_min / self.dt))
        self._isf_buffer: deque = deque([self.Gb] * lag_buffer_size, maxlen=lag_buffer_size)

        # ── Active events ──
        self._active_meals: List[ActiveMeal] = []
        self._active_insulin: List[ActiveInsulin] = []
        self._active_exercises: List[ActiveExercise] = []

        # ── Reading history ──
        self.reading_history: List[GlucoseReading] = []
        self._sim_start_time = datetime.now(timezone.utc)

        # ── Event log (for anomaly detection: "was there a logged event?") ──
        self.event_log: List[dict] = []

        logger.info(
            f"BergmanEngine initialized — Gb={self.Gb}, Ib={self.Ib}, "
            f"noise_σ={self.noise_std}, ISF_lag={self.isf_lag_min}min"
        )

    # ═══════════════════════════════════════════════════════════
    #  Event Injection
    # ═══════════════════════════════════════════════════════════

    def inject_meal(self, carbs_g: float, glycemic_index: float = 55.0,
                    food_name: str = "Meal") -> None:
        """Inject a carbohydrate meal event into the simulation."""
        meal = ActiveMeal(carbs_g, glycemic_index, self.state.time_min)
        self._active_meals.append(meal)
        self.event_log.append({
            "type": "meal",
            "time_min": self.state.time_min,
            "details": {"carbs_g": carbs_g, "gi": glycemic_index, "food_name": food_name}
        })
        logger.info(
            f"[Meal Injected] {food_name}: {carbs_g}g carbs, GI={glycemic_index} "
            f"at t={self.state.time_min:.0f}min"
        )

    def inject_insulin(self, units: float, dia_hours: float = 4.0) -> None:
        """Inject a bolus insulin dose into the simulation."""
        insulin = ActiveInsulin(units, self.state.time_min, dia_hours)
        self._active_insulin.append(insulin)
        self.event_log.append({
            "type": "insulin",
            "time_min": self.state.time_min,
            "details": {"units": units, "dia_hours": dia_hours}
        })
        logger.info(f"[Insulin Injected] {units} units, DIA={dia_hours}h at t={self.state.time_min:.0f}min")

    def inject_exercise(self, duration_min: float, intensity: float = 1.0,
                        activity_name: str = "Exercise") -> None:
        """Inject an exercise event into the simulation."""
        exercise = ActiveExercise(duration_min, intensity, self.state.time_min)
        self._active_exercises.append(exercise)
        self.event_log.append({
            "type": "exercise",
            "time_min": self.state.time_min,
            "details": {"duration_min": duration_min, "intensity": intensity, "name": activity_name}
        })
        logger.info(
            f"[Exercise Injected] {activity_name}: {duration_min}min, "
            f"intensity={intensity} at t={self.state.time_min:.0f}min"
        )

    # ═══════════════════════════════════════════════════════════
    #  Core ODE Integration (RK4)
    # ═══════════════════════════════════════════════════════════

    def _compute_derivatives(self, G: float, X: float, I: float,
                             Ra: float, exercise_rate: float) -> Tuple[float, float, float]:
        """
        Compute the derivatives for the Bergman Minimal Model ODEs.

        dG/dt = -p1 * (G - Gb) - X * G + Ra - exercise_rate
        dX/dt = -p2 * X + p3 * (I - Ib)
        dI/dt = -n * (I - Ib) + insulin_input

        Returns: (dG, dX, dI)
        """
        # Glucose dynamics
        dG = -self.p1 * (G - self.Gb) - X * G + Ra - exercise_rate

        # Insulin action dynamics
        dX = -self.p2 * X + self.p3 * max(0, I - self.Ib)

        # Insulin clearance (insulin input handled separately via IOB)
        insulin_input = sum(
            ins.get_insulin_rate(self.state.time_min)
            for ins in self._active_insulin
        )
        dI = -self.n * (I - self.Ib) + insulin_input

        return dG, dX, dI

    def _rk4_step(self, G: float, X: float, I: float,
                  Ra: float, exercise_rate: float, dt: float) -> Tuple[float, float, float]:
        """
        Fourth-order Runge-Kutta integration step for the ODE system.
        Provides much better accuracy than Euler's method for the same step size.
        """
        # k1
        k1_G, k1_X, k1_I = self._compute_derivatives(G, X, I, Ra, exercise_rate)

        # k2
        k2_G, k2_X, k2_I = self._compute_derivatives(
            G + 0.5 * dt * k1_G,
            X + 0.5 * dt * k1_X,
            I + 0.5 * dt * k1_I,
            Ra, exercise_rate
        )

        # k3
        k3_G, k3_X, k3_I = self._compute_derivatives(
            G + 0.5 * dt * k2_G,
            X + 0.5 * dt * k2_X,
            I + 0.5 * dt * k2_I,
            Ra, exercise_rate
        )

        # k4
        k4_G, k4_X, k4_I = self._compute_derivatives(
            G + dt * k3_G,
            X + dt * k3_X,
            I + dt * k3_I,
            Ra, exercise_rate
        )

        # Weighted average
        G_new = G + (dt / 6.0) * (k1_G + 2 * k2_G + 2 * k3_G + k4_G)
        X_new = X + (dt / 6.0) * (k1_X + 2 * k2_X + 2 * k3_X + k4_X)
        I_new = I + (dt / 6.0) * (k1_I + 2 * k2_I + 2 * k3_I + k4_I)

        return G_new, X_new, I_new

    # ═══════════════════════════════════════════════════════════
    #  Circadian Rhythm (Dawn Phenomenon)
    # ═══════════════════════════════════════════════════════════

    def _circadian_effect(self, time_min: float) -> float:
        """
        Simulate the dawn phenomenon: a natural glucose rise between 4-8 AM.
        Uses a sinusoidal wave with a 24-hour period, peaking at ~6 AM.
        Returns mg/dL/min adjustment.
        """
        # Convert simulation time to hours in a 24-hour cycle
        hours = (time_min / 60.0) % 24.0

        # Dawn phenomenon peaks around hour 6 (6 AM)
        # Amplitude: ~8 mg/dL total swing over the cycle
        dawn_effect = 0.08 * math.sin(2 * math.pi * (hours - 2) / 24.0)

        return dawn_effect

    # ═══════════════════════════════════════════════════════════
    #  Main Simulation Step
    # ═══════════════════════════════════════════════════════════

    def step(self) -> GlucoseReading:
        """
        Advance the simulation by one output interval (5 simulated minutes).
        Internally runs multiple RK4 steps at 1-minute resolution.
        Returns a GlucoseReading with the ISF-lagged, noisy sensor value.
        """
        for _ in range(self.steps_per_output):
            # ── Compute aggregate inputs at current time ──

            # Gut glucose absorption from all active meals
            total_Ra = sum(
                meal.get_ra(self.state.time_min)
                for meal in self._active_meals
            )

            # Exercise glucose utilization from all active exercises
            total_exercise = sum(
                ex.get_exercise_rate(self.state.time_min)
                for ex in self._active_exercises
            )

            # Circadian rhythm adjustment
            circadian = self._circadian_effect(self.state.time_min)

            # ── Auto-correction insulin feedback (closed-loop basal) ──
            # When glucose exceeds target (180 mg/dL), inject a small proportional
            # insulin correction — simulates an automatic pump / Type-2 response.
            # This prevents the simulation from pegging at 500 mg/dL.
            auto_insulin_input = 0.0
            glucose_excess = self.state.G - 180.0
            if glucose_excess > 0:
                # Proportional gain: 0.005 units per mg/dL above 180, per minute
                auto_insulin_input = min(glucose_excess * 0.005, 0.5)   # cap at 0.5 U/min

            # ── RK4 integration step ──
            G_new, X_new, I_new = self._rk4_step(
                self.state.G, self.state.X, self.state.I + auto_insulin_input,
                total_Ra + circadian, total_exercise, self.dt
            )

            # ── Physiological bounds clamping ──
            G_new = max(30.0, min(G_new, 500.0))
            X_new = max(0.0, X_new)
            I_new = max(0.0, I_new)

            # ── Update ISF lag buffer ──
            self._isf_buffer.append(G_new)

            # ── ISF glucose = delayed blood glucose (first-order lag) ──
            # The ISF reading is the value from `lag_minutes` ago
            G_isf = self._isf_buffer[0]

            # ── Update state ──
            self.state.G = G_new
            self.state.X = X_new
            self.state.I = I_new
            self.state.G_isf = G_isf
            self.state.Ra = total_Ra
            self.state.exercise_rate = total_exercise
            self.state.time_min += self.dt

        # ── Clean up expired events ──
        self._active_meals = [m for m in self._active_meals if not m.is_expired(self.state.time_min)]
        self._active_insulin = [i for i in self._active_insulin if not i.is_expired(self.state.time_min)]
        self._active_exercises = [e for e in self._active_exercises if not e.is_expired(self.state.time_min)]

        # ── Apply sensor noise ──
        noise = random.gauss(0, self.noise_std)
        noisy_isf = max(30.0, min(self.state.G_isf + noise, 500.0))

        # ── Create reading ──
        sim_elapsed = timedelta(minutes=self.state.time_min)
        reading_time = self._sim_start_time + sim_elapsed

        reading = GlucoseReading(
            timestamp=reading_time,
            glucose_mg_dl=round(noisy_isf, 1),
            blood_glucose_mg_dl=round(self.state.G, 1),
            is_noisy=True
        )

        # ── Store in history ──
        self.reading_history.append(reading)

        # ── Trim history to buffer size ──
        settings = get_settings()
        if len(self.reading_history) > settings.HISTORY_BUFFER_SIZE * 2:
            self.reading_history = self.reading_history[-settings.HISTORY_BUFFER_SIZE:]

        return reading

    # ═══════════════════════════════════════════════════════════
    #  Accessors
    # ═══════════════════════════════════════════════════════════

    def get_current_iob(self) -> float:
        """Calculate total active insulin-on-board (units)."""
        return sum(
            ins.get_iob(self.state.time_min)
            for ins in self._active_insulin
        )

    def is_exercising(self) -> bool:
        """Check if any exercise is currently active (not just lingering)."""
        return any(
            ex.is_active(self.state.time_min)
            for ex in self._active_exercises
        )

    def get_recent_readings(self, n: int = 72) -> List[GlucoseReading]:
        """Get the last N glucose readings from history."""
        return self.reading_history[-n:]

    def has_recent_event(self, within_minutes: float = 30.0) -> bool:
        """
        Check if any meal or activity event was logged within the
        specified time window. Used for anomaly detection.
        """
        cutoff = self.state.time_min - within_minutes
        return any(e["time_min"] >= cutoff for e in self.event_log)

    def get_recent_events(self, within_minutes: float = 60.0) -> List[dict]:
        """Get events logged within the last N minutes."""
        cutoff = self.state.time_min - within_minutes
        return [e for e in self.event_log if e["time_min"] >= cutoff]

    def reset(self) -> None:
        """Reset the engine to initial state."""
        self.__init__()
