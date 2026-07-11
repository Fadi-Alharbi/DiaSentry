"""
DiaSentry — ADA Clinical Guidelines Knowledge Base
=====================================================
Curated clinical guideline chunks from the American Diabetes Association (ADA)
Standards of Care, formatted for semantic retrieval via RAG.

Each chunk is a self-contained clinical protocol or guidance statement
that the LLM can retrieve and reason over.

Source: ADA Standards of Care in Diabetes — 2024
        (condensed and structured for agent consumption)
"""

ADA_GUIDELINE_CHUNKS = [
    # ═══════════════════════════════════════════════════════════
    #  Hypoglycemia Management
    # ═══════════════════════════════════════════════════════════
    {
        "id": "hypo_rule_of_15",
        "topic": "Hypoglycemia Treatment - Rule of 15",
        "content": (
            "HYPOGLYCEMIA TREATMENT PROTOCOL (Rule of 15):\n"
            "Level 1 Hypoglycemia (glucose 54-70 mg/dL):\n"
            "1. Consume 15 grams of fast-acting carbohydrates immediately.\n"
            "   Options: 4 glucose tablets, 150mL (½ cup) orange juice, 150mL regular soda, "
            "1 tablespoon honey, or 1 tablespoon sugar.\n"
            "2. Wait 15 minutes and recheck blood glucose.\n"
            "3. If still below 70 mg/dL, repeat step 1.\n"
            "4. Once glucose normalizes, eat a balanced snack with protein and complex carbs "
            "(e.g., cheese with crackers, peanut butter on whole wheat bread).\n"
            "Do NOT over-treat — excess carbs can cause rebound hyperglycemia."
        )
    },
    {
        "id": "hypo_severe",
        "topic": "Severe Hypoglycemia - Emergency Protocol",
        "content": (
            "SEVERE HYPOGLYCEMIA (Level 2, glucose <54 mg/dL):\n"
            "This is a medical emergency requiring immediate action.\n"
            "If conscious: Consume 20-30g fast-acting carbs immediately (juice, glucose gel).\n"
            "If unconscious or unable to swallow: Do NOT give food or liquid by mouth.\n"
            "  - Administer glucagon injection (1mg IM) or nasal glucagon (3mg intranasal).\n"
            "  - Call emergency services (911) immediately.\n"
            "  - Place the person in recovery position.\n"
            "After recovery: Monitor glucose every 15 min for 2 hours.\n"
            "Do NOT sleep until glucose is stable above 100 mg/dL.\n"
            "Report the episode to your healthcare team within 24 hours."
        )
    },
    {
        "id": "hypo_prevention",
        "topic": "Hypoglycemia Prevention Strategies",
        "content": (
            "PREVENTING HYPOGLYCEMIA:\n"
            "1. Never skip meals — eat at regular intervals (every 4-5 hours).\n"
            "2. Always carry fast-acting glucose (tablets, juice box, candy).\n"
            "3. Check glucose before driving — must be >100 mg/dL.\n"
            "4. Reduce insulin dose before planned exercise (consult physician for amount).\n"
            "5. Have a carbohydrate snack before bedtime if glucose <120 mg/dL.\n"
            "6. Limit alcohol intake — alcohol impairs liver glucose production.\n"
            "7. If hypoglycemia occurs >2x per week, contact your healthcare team "
            "to adjust medication doses.\n"
            "8. Consider Continuous Glucose Monitoring (CGM) with low glucose alerts."
        )
    },
    {
        "id": "hypo_exercise",
        "topic": "Preventing Exercise-Induced Hypoglycemia",
        "content": (
            "EXERCISE AND HYPOGLYCEMIA PREVENTION:\n"
            "• Check glucose before exercise. If <90 mg/dL, consume 15-30g carbs first.\n"
            "• If glucose 90-150 mg/dL: safe to exercise, but have snacks available.\n"
            "• If glucose >250 mg/dL: check ketones. If positive, do NOT exercise.\n"
            "• For exercise >60 minutes: consume 15-30g carbs every 30-60 minutes.\n"
            "• Reduce bolus insulin by 25-75% for the meal before exercise.\n"
            "• Exercise increases insulin sensitivity for 24-48 hours — monitor closely.\n"
            "• Avoid exercising during peak insulin action (2-4 hours post-injection).\n"
            "• Post-exercise hypoglycemia can occur 6-15 hours later (nocturnal risk)."
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  Hyperglycemia Management
    # ═══════════════════════════════════════════════════════════
    {
        "id": "hyper_correction",
        "topic": "Hyperglycemia Correction Protocol",
        "content": (
            "HYPERGLYCEMIA CORRECTION (glucose >180 mg/dL):\n"
            "Mild (180-250 mg/dL):\n"
            "1. Drink water (at least 250mL every 30 minutes).\n"
            "2. Take correction insulin dose as prescribed by your physician.\n"
            "3. Go for a 15-20 minute moderate walk if feeling well.\n"
            "4. Avoid eating until glucose begins to drop.\n"
            "5. Recheck glucose after 1 hour.\n\n"
            "Severe (>250 mg/dL):\n"
            "1. Check urine or blood ketones if available.\n"
            "2. If ketones positive: do NOT exercise, contact physician immediately.\n"
            "3. Take correction insulin as prescribed.\n"
            "4. Drink water aggressively (250mL every 20 minutes).\n"
            "5. If >300 mg/dL with symptoms (nausea, vomiting, rapid breathing), "
            "go to the emergency room — risk of Diabetic Ketoacidosis (DKA).\n"
            "6. Do NOT eat until glucose drops below 250 mg/dL."
        )
    },
    {
        "id": "hyper_prevention",
        "topic": "Hyperglycemia Prevention Strategies",
        "content": (
            "PREVENTING HYPERGLYCEMIA:\n"
            "1. Take all medications/insulin exactly as prescribed — never skip doses.\n"
            "2. Count carbohydrates and match insulin doses appropriately.\n"
            "3. Eat vegetables and protein BEFORE carbohydrates in each meal.\n"
            "4. Limit simple carbohydrates: white bread, sugary drinks, candy, pastries.\n"
            "5. Split large meals into 5-6 smaller portions throughout the day.\n"
            "6. Walk for 10-15 minutes after every meal to flatten the glucose spike.\n"
            "7. Manage stress — cortisol raises blood glucose.\n"
            "8. Stay hydrated — dehydration concentrates blood glucose.\n"
            "9. Review medications during illness — 'sick day rules' may require dose adjustments."
        )
    },
    {
        "id": "hyper_postmeal",
        "topic": "Post-Meal Glucose Spike Management",
        "content": (
            "MANAGING POST-MEAL GLUCOSE SPIKES:\n"
            "• Take rapid-acting insulin 15-20 minutes BEFORE eating (pre-bolus).\n"
            "• Eat protein and fiber first, carbohydrates last (food order effect).\n"
            "• Choose low-glycemic-index foods (GI <55): lentils, vegetables, whole grains.\n"
            "• Avoid high-GI foods (GI >70): white rice, white bread, potatoes, watermelon.\n"
            "• A 15-minute walk after meals significantly reduces post-meal peaks.\n"
            "• Add vinegar or lemon juice to meals — may reduce glycemic response.\n"
            "• For pizza/pasta: consider split bolus (50% now, 50% extended over 2-3 hours).\n"
            "• Post-meal target: glucose should be <180 mg/dL at 2 hours after eating."
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  Glucose Target Ranges
    # ═══════════════════════════════════════════════════════════
    {
        "id": "targets_general",
        "topic": "ADA Glucose Target Ranges",
        "content": (
            "ADA RECOMMENDED GLUCOSE TARGETS:\n"
            "• Fasting / Pre-meal: 80-130 mg/dL\n"
            "• 2-hour Post-meal: <180 mg/dL\n"
            "• Bedtime: 100-140 mg/dL\n"
            "• Time-in-Range (TIR): >70% of readings between 70-180 mg/dL\n"
            "• Time-below-Range (TBR): <4% of readings below 70 mg/dL\n"
            "• Time-below-Range (Level 2): <1% of readings below 54 mg/dL\n"
            "• Time-above-Range (TAR): <25% of readings above 180 mg/dL\n"
            "• A1C Target: <7.0% for most adults\n"
            "• Glucose variability (CV): <36% indicates stable control.\n"
            "Note: Targets may be more relaxed for elderly, children, or those "
            "with hypoglycemia unawareness."
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  Insulin Management
    # ═══════════════════════════════════════════════════════════
    {
        "id": "insulin_correction",
        "topic": "Insulin Correction Factor and Dosing",
        "content": (
            "INSULIN CORRECTION FACTOR (ICF):\n"
            "The correction factor estimates how much 1 unit of rapid-acting insulin "
            "will lower blood glucose.\n"
            "• Rule of 1800: ICF = 1800 / Total Daily Dose (TDD)\n"
            "  Example: TDD = 45 units → ICF = 1800/45 = 40 mg/dL per unit\n"
            "• Correction dose = (Current glucose - Target) / ICF\n"
            "  Example: Glucose 250, Target 120 → (250-120)/40 = 3.25 → round to 3 units\n\n"
            "INSULIN-TO-CARB RATIO (ICR):\n"
            "• Rule of 500: ICR = 500 / TDD\n"
            "  Example: TDD = 50 units → ICR = 500/50 = 1 unit per 10g carbs\n"
            "• Meal dose = Carbs consumed (g) / ICR\n\n"
            "IMPORTANT: These are estimates. Individual ratios must be determined "
            "by your healthcare team through systematic testing."
        )
    },
    {
        "id": "insulin_on_board",
        "topic": "Insulin-on-Board and Stacking Prevention",
        "content": (
            "INSULIN-ON-BOARD (IOB) AND STACKING RISK:\n"
            "• IOB = the amount of previously injected insulin still active in the body.\n"
            "• Rapid-acting insulin (Humalog, NovoLog) has a Duration of Action of 3-5 hours.\n"
            "• Peak action occurs 1-2 hours after injection.\n"
            "• NEVER give a correction dose without accounting for IOB.\n"
            "• Insulin stacking = giving repeated correction doses before previous doses peak.\n"
            "  This is the #1 cause of severe hypoglycemia.\n"
            "• Wait at least 3-4 hours between correction doses.\n"
            "• CGM systems can show IOB — always check before correcting.\n"
            "• If glucose is still high but IOB >2 units: WAIT, do not add more insulin."
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  Exercise Guidelines
    # ═══════════════════════════════════════════════════════════
    {
        "id": "exercise_general",
        "topic": "Exercise Recommendations for Diabetes",
        "content": (
            "ADA EXERCISE RECOMMENDATIONS FOR DIABETES:\n"
            "• 150 minutes/week of moderate-intensity aerobic exercise (brisk walking, cycling).\n"
            "• 2-3 sessions/week of resistance training (weights, bands).\n"
            "• Avoid more than 2 consecutive days without exercise.\n"
            "• Moderate walking (15-20 min) after meals effectively reduces post-meal spikes.\n"
            "• Exercise lowers blood glucose both during and after activity.\n"
            "• High-intensity exercise may temporarily RAISE glucose (stress hormones).\n"
            "• Check glucose before, during (if >60 min), and after exercise.\n"
            "• Stay hydrated — drink water before, during, and after activity."
        )
    },
    {
        "id": "exercise_glucose_response",
        "topic": "How Different Exercise Types Affect Glucose",
        "content": (
            "EXERCISE TYPE AND GLUCOSE RESPONSE:\n"
            "Aerobic exercise (walking, jogging, swimming, cycling):\n"
            "  → Generally LOWERS glucose during and after activity.\n"
            "  → Effect: -20 to -50 mg/dL during 30 min of moderate exercise.\n"
            "  → Post-exercise insulin sensitivity boost lasts 24-48 hours.\n\n"
            "Anaerobic/Resistance exercise (weights, sprints, HIIT):\n"
            "  → May RAISE glucose initially due to adrenaline and cortisol release.\n"
            "  → Followed by a gradual decrease over 1-2 hours.\n"
            "  → Mixed aerobic+resistance is ideal for glucose management.\n\n"
            "Walking after meals:\n"
            "  → 10-15 minutes of post-meal walking reduces peak glucose by 15-25%.\n"
            "  → This is one of the most effective, low-risk interventions."
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  Meal Planning
    # ═══════════════════════════════════════════════════════════
    {
        "id": "meal_planning",
        "topic": "Diabetes Meal Planning - Carbohydrate Counting",
        "content": (
            "CARBOHYDRATE COUNTING AND MEAL PLANNING:\n"
            "• Total daily carb intake: 45-65% of total calories (individualized).\n"
            "• Typical meal: 30-60g carbs. Snack: 15-20g carbs.\n"
            "• Measure portions — visual estimates are often 30-50% off.\n"
            "• Read nutrition labels — check serving size AND total carbs.\n"
            "• Fiber reduces net glycemic impact: Net carbs = Total carbs - Fiber.\n"
            "• Protein and fat slow carb absorption (lower GI effect).\n"
            "• Distribute carbs evenly across meals to prevent large spikes.\n"
            "• Avoid liquid carbs (juice, soda) unless treating hypoglycemia."
        )
    },
    {
        "id": "glycemic_index",
        "topic": "Glycemic Index Guide for Common Foods",
        "content": (
            "GLYCEMIC INDEX (GI) REFERENCE TABLE:\n"
            "LOW GI (<55) — Minimal glucose spike:\n"
            "  Lentils (25), Chickpeas (28), Kidney beans (24), Apples (36),\n"
            "  Oranges (43), Yogurt (plain, 36), Oats/steel-cut (42),\n"
            "  Sweet potatoes (44), Whole wheat bread (51), Milk (39)\n\n"
            "MEDIUM GI (55-69):\n"
            "  Basmati rice (58), Brown rice (55), Banana (51), Pineapple (59),\n"
            "  Whole grain pita (57), Couscous (65)\n\n"
            "HIGH GI (>70) — Rapid glucose spike:\n"
            "  White bread (75), White rice (73), Potatoes (78), Watermelon (76),\n"
            "  Corn flakes (81), Instant oatmeal (79), Dates (103),\n"
            "  Glucose tablets (100), Orange juice (50, but fast-absorbing liquid)\n\n"
            "STRATEGY: Replace high-GI with low-GI alternatives at each meal."
        )
    },
    {
        "id": "fast_acting_carbs",
        "topic": "Fast-Acting Carbohydrates for Hypoglycemia Treatment",
        "content": (
            "FAST-ACTING CARBOHYDRATE OPTIONS (15g each):\n"
            "Best choices for treating low blood sugar:\n"
            "• 4 glucose tablets (most precise and reliable)\n"
            "• 150mL (½ cup) orange juice\n"
            "• 150mL regular (non-diet) soda\n"
            "• 1 tablespoon honey\n"
            "• 1 tablespoon sugar dissolved in water\n"
            "• 6-8 hard candies (e.g., Life Savers)\n"
            "• 1 small box (15g) raisins\n"
            "• Glucose gel tube (15g)\n\n"
            "AVOID for hypo treatment:\n"
            "• Chocolate (fat slows absorption)\n"
            "• Protein bars (too slow)\n"
            "• Diet drinks (zero carbs)\n"
            "• Fruit with skin (fiber slows absorption)"
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  Anomaly / Rapid Change Guidance
    # ═══════════════════════════════════════════════════════════
    {
        "id": "rapid_change",
        "topic": "Managing Rapid Glucose Changes",
        "content": (
            "RAPID GLUCOSE CHANGE MANAGEMENT:\n"
            "A rate of change >2 mg/dL/min or <-2 mg/dL/min is considered rapid.\n\n"
            "If rapidly RISING:\n"
            "• Verify with fingerstick if possible — CGM may lag.\n"
            "• Check: Did you eat recently? Did you miss insulin?\n"
            "• Drink water and take correction insulin if prescribed.\n"
            "• Do NOT stack insulin — check IOB first.\n\n"
            "If rapidly FALLING:\n"
            "• Prepare fast-acting carbs NOW — don't wait for the alarm.\n"
            "• If >100 mg/dL but falling fast: eat 15g carbs preemptively.\n"
            "• If exercising: STOP exercise and eat.\n"
            "• Do NOT drive or operate machinery.\n"
            "• Stay alert — rapid drops can cause loss of consciousness.\n\n"
            "Unexplained rapid change (no meal/exercise/insulin):\n"
            "• Could indicate sensor malfunction — verify with fingerstick.\n"
            "• Stress, illness, or hormonal changes can cause unexplained spikes.\n"
            "• Dawn phenomenon causes early-morning rises (4-8 AM).\n"
            "• Report recurring unexplained changes to your healthcare team."
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  Sick Day Rules
    # ═══════════════════════════════════════════════════════════
    {
        "id": "sick_day",
        "topic": "Sick Day Management for Diabetes",
        "content": (
            "SICK DAY RULES FOR DIABETES:\n"
            "• NEVER stop taking insulin, even if not eating.\n"
            "• Check glucose every 2-4 hours.\n"
            "• Check ketones if glucose >250 mg/dL.\n"
            "• Stay hydrated: sip water or sugar-free fluids every 15 minutes.\n"
            "• If unable to eat solid food: consume liquids with carbs "
            "(clear broth, gelatin, popsicles).\n"
            "• Contact physician if: glucose >300 for >2 readings, positive ketones, "
            "vomiting >2 hours, fever >101°F (38.3°C).\n"
            "• Some medications (SGLT2 inhibitors) should be paused during illness."
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  Bedtime & Overnight Management
    # ═══════════════════════════════════════════════════════════
    {
        "id": "bedtime_management",
        "topic": "Bedtime and Overnight Glucose Management",
        "content": (
            "BEDTIME GLUCOSE MANAGEMENT:\n"
            "• Target bedtime glucose: 100-140 mg/dL.\n"
            "• If <100 mg/dL at bedtime: eat a snack with protein + complex carbs "
            "(e.g., peanut butter crackers, cheese with whole grain bread).\n"
            "• If >180 mg/dL at bedtime: take correction insulin (accounting for IOB).\n"
            "• Nocturnal hypoglycemia risk factors: exercise that day, alcohol, "
            "missed meals, excess insulin.\n"
            "• Set CGM low alert at 70 mg/dL with predictive alert if available.\n"
            "• Dawn phenomenon (4-8 AM rise): may need basal insulin adjustment.\n"
            "• Never go to bed with active IOB >3 units without monitoring plan."
        )
    },

    # ═══════════════════════════════════════════════════════════
    #  General Wellness & Context
    # ═══════════════════════════════════════════════════════════
    {
        "id": "hydration",
        "topic": "Hydration and Blood Glucose",
        "content": (
            "HYDRATION AND GLUCOSE MANAGEMENT:\n"
            "• Dehydration concentrates blood glucose — readings appear higher.\n"
            "• Aim for 8-10 glasses (2-2.5L) of water daily.\n"
            "• During hyperglycemia: increase water intake to help kidneys clear glucose.\n"
            "• Avoid sugary drinks: soda, sweetened tea, fruit juice (except for hypo treatment).\n"
            "• Coffee (black, unsweetened) is generally safe but may raise glucose in some people.\n"
            "• Alcohol impairs liver glucose production — risk of delayed hypoglycemia 6-24h later."
        )
    },
    {
        "id": "stress_glucose",
        "topic": "Stress and Blood Glucose",
        "content": (
            "STRESS AND BLOOD GLUCOSE:\n"
            "• Mental stress raises cortisol and adrenaline, which increase blood glucose.\n"
            "• Physical stress (illness, injury, surgery) also raises glucose significantly.\n"
            "• Unexplained glucose spikes may be stress-related.\n"
            "• Stress management techniques: deep breathing, meditation, walking, "
            "adequate sleep (7-8 hours).\n"
            "• Chronic stress can worsen insulin resistance.\n"
            "• Consider stress as a factor when glucose is unexpectedly high."
        )
    },
]
