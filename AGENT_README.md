# AGENT_README.md

## 1. PROJECT IDENTITY & PHILOSOPHY

**Project Name:** Zero-Idle Gym Station
**Hardware Context:** Dual RTX 3090 Workstation (Local Host).
**Core Philosophy:** "The Clerk & The Muscle."

* **The Clerk (Idle):** Lightweight FastAPI + SQLite. Runs 24/7 via Systemd Socket Activation. Uses 0MB RAM when idle.
* **The Muscle (Active):** Heavy Python scripts/LLM. Only triggered manually for weekly updates.

## 2. FILE SYSTEM MAP

* `main.py` -> **The API Server.** Handles HTTP requests from mobile. Reads/Writes to `gym.db`.
* `init_db.py` -> **The Database Seeder.** Creates tables and seeds Week 1 from the Excel Master.
* `generate_routine.py` -> **The Compiler.** Converts Python dictionaries (logic) into `gym_routine_master.xlsx`.
* `gym.db` -> **The State.** SQLite database holding the active plan and history.
* `gym_routine_master.xlsx` -> **The Blueprint.** Intermediate file used for visualization or re-seeding.

## 3. DATA ARCHITECTURE (CRITICAL)

**Database:** SQLite
**Constraint:** SQLite does not support Arrays. We store list data as **JSON Strings**.

### Table: `workout_plan` (The Target)

* `id`: PK
* `week_id`: Integer (Increments weekly).
* `exercise`: Text.
* `target_weight_json`: **TEXT (JSON)**.
* *Format:* `"[22.0, 19.5, 17.0]"`
* *Agent Instruction:* MUST use `json.loads()` on read and `json.dumps()` on write.


* `strategy`: Text (Determines how the AI updates this next week).
* `rounding`: Real (e.g., 2.5, 1.25). The minimum plate increment.

### Table: `workout_logs` (The History)

* `actual_weight_json`: **TEXT (JSON)**. Example: `"[22, 22, 20]"` (User might override targets).
* `actual_reps_json`: **TEXT (JSON)**. Example: `"[10, 8, 7]"`.

## 4. LOGIC PRIMITIVES

The project uses specific algorithms to generate weights.

### A. The "Anchor Weight" Logic (Drop Sets)

Used for almost all exercises (Dumbbells, Machines, Cables).

* **Input:** Single Float (e.g., `22kg`).
* **Transformation:** The system automatically calculates a drop set based on `sets` and `rounding`.
* **Formula:** `[Weight, Weight - Rounding, Weight - 2*Rounding]`
* **Example:** Input `22`, Rounding `2.5` -> Result `[22.0, 19.5, 17.0]`.

### B. The "Static" Logic (Abs)

* **Module:** Abs routine is defined as a constant list in `generate_routine.py`.
* **Behavior:** It is programmatically appended to Days 1, 2, 4, 5.
* **Update Rule:** Never change weights. Always `[0, 0, 0]`.

### C. The "Periodized" Logic (Bench Press Only)

* **Context:** Day 1 Bench Press follows a strict 6-week strength cycle.
* **Behavior:** Weights are uniform (Straight Sets). e.g., `[90, 90, 90, 90, 90]`.
* **Cycle:** 5x5 -> 4x4 -> 3x3 -> 2x2 -> Deload -> PR.

## 5. UPDATE RULES (FOR AI AGENTS)

When the Agent is called to generate "Next Week's Plan", it must follow these Strategy Tags:

1. **`strategy="linear"`**:
* Read `actual_reps`.
* **Rule:** If Reps in Set 1 >= Target Reps (Anchor), increase Anchor Weight by `rounding`.
* Else, keep Anchor Weight same.
* *Recalculate* the drop-set array based on the new Anchor.


2. **`strategy="variable_drop"`**:
* Read `actual_reps` per set.
* **Rule:** If Set X reps >= 8, maintain weight for Set X+1 (do not drop).
* *Optimization:* Allow independent weight movement per set.


3. **`strategy="periodized_bench"`**:
* Read `user_stats` table for `current_bench_cycle_week`.
* Increment Week.
* Look up % logic for new week.
* Calculate new weight based on 1RM.


4. **`strategy="static"`**:
* Copy exact rows from previous week. Do not change values.



## 6. DEPLOYMENT CONTEXT

* **Network:** Accessed via Tailscale / ZeroTier IP.
* **App:** Frontend expects `GET /workout/{day_id}` to return parsed JSON arrays, not strings.
* **Lifecycle:**
1. User opens App -> Socket wakes `main.py`.
2. User Logs Data -> Saved to `gym.db`.
3. User requests "New Week" -> `main.py` triggers External AI Script.
4. Script reads DB -> Writes new Week to DB -> Kills itself.