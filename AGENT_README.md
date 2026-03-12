# Zero-Idle Gym AI - Backend Architecture (v2)

This document provides a high-level overview of the fully redesigned backend architecture for GYM_AI.

The architecture was recently modernised to rely on a pure Python, 100% deterministic heuristic engine for progression, completely removing all dependency on LLMs for workout generation. The codebase now strictly adheres to a service-oriented architecture, using SQLAlchemy as the ORM, and Pydantic for robust request validation in FastAPI.

---

## Directory Structure Overview

```text
backend/
├── main.py                  # FastAPI routes ONLY (endpoints & validation)
├── gym.db                   # Single source of truth (SQLite)
├── .env                     # Environment variables
├── db/
│   ├── __init__.py 
│   ├── schema.py            # SQLAlchemy ORM models
│   └── init.py              # Initialisation and seeding logic
├── services/
│   ├── __init__.py
│   ├── progression.py       # Core deterministic heuristic engine (NO LLM)
│   ├── session.py           # CRUD operations for Sessions and Sets
│   └── metrics.py           # Integrations for Apple Health and Renpho
├── migrations/
│   └── migrate_legacy.py    # One-time script to ingest legacy JSON/CSV data into SQLite
└── config/
    ├── exercises.json       # Source of truth for exercise metadata and tiers
    └── targets.json         # User fitness goals (weight target, bench PR)
```

---

## Technical Stack & Standards
- **Framework**: FastAPI
- **Validation**: Pydantic
- **ORM**: SQLAlchemy
- **Database**: SQLite (`gym.db`)
- **Progression Logic**: Pure Python, custom deterministic heuristics.

---

## Core Components

### 1. Database & ORM (`backend/db/`)
The database is defined in `schema.py` and maintains a relational structure tracking workouts down to individual sets (`sets` table), linked to individual exercises per session (`session_exercises`), rolled up to a specific gym day (`sessions`).

- **Key Entity Hierarchy**: `Session` → `SessionExercise` → `Set`
- **Exercises Catalog**: The `exercises` table holds the master list (seeded from `config/exercises.json`). Crucially, the `tier` attribute (primary/heavy/small) dictates rep floors and ceilings for progressive overload.
- **Metrics Table**: Tracks `daily_metrics` (Apple Health) and `body_composition` (Renpho/manual entry), offering physiological signals to the progression engine.
- **Bench Cycle tracking**: The `bench_cycle` table manages the 6-week periodised powerlifting plan exclusively for the Bench Press, detached from standard heuristic rules.

### 2. Services Layer (`backend/services/`)
Business logic is strictly decoupled from the web layer:
- **`progression.py`**: The "brain" of GYM_AI. This engine inspects past performance and physiological trends (like bodyweight dropping or plateauing) to aggressively step-load weight or slowly add reps. It features auto-detection for anomalous fatigue (checking if an exercise was performed significantly later in a session than usual). 
- **`session.py`**: Manages the persistence of workout logs, computing metrics like the Estimated 1-Rep Max (Epley Formula) for every single set automatically upon database insertion.
- **`metrics.py`**: Webhook receivers and parsers for third-party health data.

### 3. Routes (`backend/main.py`)
`main.py` functions exclusively as a traffic cop. It defines HTTP endpoints (`/sessions`, `/progression`, `/metrics`, `/config`), depends on localized `get_db()` scoped instances, implements Pydantic payload models to sanitize everything, and blindly forwards tasks to the `services` layer. 

### 4. Zero-Data-Loss Migration (`backend/migrations/`)
To preserve legacy workouts that were stored exclusively as flat JSON files in the `/data` directory, a one-off `migrate_legacy.py` is available. When executed, it safely bulk-reads cold storage JSON logs, creates the relevant foreign-key relationships in `gym.db`, and back-calculates `e1rm` constraints onto all historical sets.

---

## Operational Mechanics

### The Progression Engine (Heuristic vs Cycle)
Because barbell bench-pressing fundamentally behaves differently over time than isolated machine variants, two distinct logic paths govern weight recommendations:

1. **Static Periodisation (Bench Press ONLY)**: Follows a rigid 6-week cycle mapped to intensity percentages. Progress is solely dependent on completing the Week 6 PR attempt. Handled by `get_bench_cycle_targets()`.
2. **Aggressive Dynamic Overload (Everything Else)**: Evaluates `compute_next_week()`. The system analyses:
   - Historical drop-rate (fatigue variance from set 1 to 3)
   - E1RM trends
   - Bodyweight gradients (to intelligently boost progression when eating in a caloric surplus)
   - Exercise sequence fatigue

If an anomaly is spotted (e.g. failing minimum reps, but only because the machine was used 5th instead of 2nd on a given day), the system gracefully holds weight instead of permanently deloading the user.