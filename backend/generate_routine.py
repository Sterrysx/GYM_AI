import json
import pandas as pd


def strict_list(weight, sets, rounding=2.5):
    """
    Generates the default "Drop Set" plan.
    - Set 1: Weight
    - Set 2: Weight - Rounding
    - Set 3: Weight - (2 * Rounding)
    """
    if isinstance(weight, list):
        return json.dumps(weight)
    
    # Generate the default drop sequence
    weight_list = []
    current_weight = float(weight)
    
    for i in range(sets):
        safe_weight = max(0, current_weight)
        weight_list.append(safe_weight)
        current_weight -= rounding
        
    return json.dumps(weight_list)


def uniform_list(weight, sets):
    """
    Generates a uniform weight list for periodized exercises.
    Example: weight=90, sets=5 -> "[90.0, 90.0, 90.0, 90.0, 90.0]"
    """
    return json.dumps([float(weight)] * sets)


def explicit_list(weights):
    """
    Return a pre-defined weight array as a JSON string.
    Used for small-muscle exercises where auto-drop is too aggressive.
    Example: [10, 10, 5] -> "[10, 10, 5]"
    """
    return json.dumps([float(w) for w in weights])

# ---------------------------------------------------------
# 1. DEFINE THE CONSTANT MODULES (The Abs Routine)
# ---------------------------------------------------------
abs_routine = [
    {"Exercise": "Abs: Figure 8's", "Sets": 1, "Target Reps": "30s", "Baseline Weight (kg)": 0, "Strategy": "static", "Rounding": 0, "Superset Group": "Abs"},
    {"Exercise": "Abs: Hands Back Raises", "Sets": 1, "Target Reps": "60s", "Baseline Weight (kg)": 0, "Strategy": "static", "Rounding": 0, "Superset Group": "Abs"},
    {"Exercise": "Abs: Lower abs up/down", "Sets": 1, "Target Reps": "60s", "Baseline Weight (kg)": 0, "Strategy": "static", "Rounding": 0, "Superset Group": "Abs"},
    {"Exercise": "Abs: Seated 8's Left", "Sets": 1, "Target Reps": "60s", "Baseline Weight (kg)": 0, "Strategy": "static", "Rounding": 0, "Superset Group": "Abs"},
    {"Exercise": "Abs: Seated 8's Right", "Sets": 1, "Target Reps": "60s", "Baseline Weight (kg)": 0, "Strategy": "static", "Rounding": 0, "Superset Group": "Abs"},
    {"Exercise": "Abs: Scissor V Ups", "Sets": 1, "Target Reps": "30s", "Baseline Weight (kg)": 0, "Strategy": "static", "Rounding": 0, "Superset Group": "Abs"},
    {"Exercise": "Abs: 21 Crunch", "Sets": 1, "Target Reps": "30s", "Baseline Weight (kg)": 0, "Strategy": "static", "Rounding": 0, "Superset Group": "Abs"},
]

# ---------------------------------------------------------
# 2. DEFINE THE DAILY WORKOUTS (Anchor Weight Logic)
# ---------------------------------------------------------
daily_workouts = {
    1: [ # Day 1: Push
        # 1. Barbell Bench Press (Periodized — uniform weight across all sets)
        # Week 1: 5x5 @ 75% of 90kg 1RM = 67.5kg
        {
            "Day Name": "Push", "Exercise": "Barbell Bench Press", 
            "Sets": 5, "Target Reps": "5", 
            "Weight Input": 67.5, "Strategy": "periodized_bench", "Rounding": 2.5, "Superset Group": None
        },
        # Superset A
        {"Day Name": "Push", "Exercise": "Low Cable Flyes", "Sets": 3, "Target Reps": "6-10", "Weight Input": [7.5, 7.5, 5], "Strategy": "linear", "Rounding": 2.5, "Superset Group": "A"},
        {"Day Name": "Push", "Exercise": "Frontal Plate Raises", "Sets": 3, "Target Reps": "6-10", "Weight Input": [10, 5, 5], "Strategy": "linear", "Rounding": 5, "Superset Group": "A"},
        
        # Superset B
        {"Day Name": "Push", "Exercise": "Overhead Tricep Extension (Cable)", "Sets": 4, "Target Reps": "6-10", "Weight Input": [65, 60, 55, 50], "Strategy": "linear", "Rounding": 5, "Superset Group": "B"},
        {"Day Name": "Push", "Exercise": "Lateral Dumbbell Raises", "Sets": 4, "Target Reps": "12", "Weight Input": [8, 7, 6, 6], "Strategy": "linear", "Rounding": 1, "Superset Group": "B"},
        
        # Superset C
        {"Day Name": "Push", "Exercise": "Tricep Pushdowns", "Sets": 4, "Target Reps": "12", "Weight Input": [85, 80, 75, 70], "Strategy": "linear", "Rounding": 5, "Superset Group": "C"},
        {"Day Name": "Push", "Exercise": "Lateral Cable Raises", "Sets": 4, "Target Reps": "12", "Weight Input": [3.75, 3.75, 2.5, 2.5], "Strategy": "linear", "Rounding": 1.25, "Superset Group": "C"},
    ],

    2: [ # Day 2: Pull
        {"Day Name": "Pull", "Exercise": "Lat Pulldowns", "Sets": 3, "Target Reps": "12", "Weight Input": [70, 60, 50], "Strategy": "linear", "Rounding": 2.5, "Superset Group": None},
        
        # Superset A
        {"Day Name": "Pull", "Exercise": "Machine Closed Row", "Sets": 3, "Target Reps": "12", "Weight Input": [47, 42, 37], "Strategy": "linear", "Rounding": 2.5, "Superset Group": "A"},
        {"Day Name": "Pull", "Exercise": "Standing Finger Plate Curls", "Sets": 3, "Target Reps": "20", "Weight Input": [5, 5, 5], "Strategy": "linear", "Rounding": 5, "Superset Group": "A"},
        
        # Superset B
        {"Day Name": "Pull", "Exercise": "Cable Bicep Open Curls", "Sets": 3, "Target Reps": "12", "Weight Input": [20, 17.5, 15], "Strategy": "linear", "Rounding": 2.5, "Superset Group": "B"},
        {"Day Name": "Pull", "Exercise": "Reverse Cable Flyes", "Sets": 3, "Target Reps": "15", "Weight Input": [3.75, 2.5, 2.5], "Strategy": "linear", "Rounding": 1.25, "Superset Group": "B"},
        
        # Superset C
        {"Day Name": "Pull", "Exercise": "Dumbbell Hammer Curls", "Sets": 3, "Target Reps": "12", "Weight Input": [18, 18, 16], "Strategy": "linear", "Rounding": 2, "Superset Group": "C"},
        {"Day Name": "Pull", "Exercise": "Trapezoid Raises", "Sets": 3, "Target Reps": "12", "Weight Input": [24, 22, 20], "Strategy": "linear", "Rounding": 2, "Superset Group": "C"},
    ],

    3: [ # Day 3: Lower Body
        # Superset A
        {"Day Name": "Lower Body", "Exercise": "Hip Abduction Machine", "Sets": 3, "Target Reps": "20", "Weight Input": [105, 95, 85], "Strategy": "linear", "Rounding": 10, "Superset Group": "A"},
        {"Day Name": "Lower Body", "Exercise": "Glute Machine", "Sets": 3, "Target Reps": "15", "Weight Input": [45, 35, 35], "Strategy": "linear", "Rounding": 10, "Superset Group": "A"},
        
        # Superset B
        {"Day Name": "Lower Body", "Exercise": "Lying Leg Curls", "Sets": 3, "Target Reps": "12","Weight Input" : [21, 21, 14],  	"Strategy":"linear","Rounding" :7,"Superset Group":"B"},
        {"Day Name": "Lower Body", "Exercise": "Leg Extensions", "Sets": 3, "Target Reps": "12","Weight Input" : [40, 35, 30],  	"Strategy":"linear","Rounding" :7,"Superset Group":"B"},
        
        # Superset C
        {"Day Name": "Lower Body", "Exercise": "Machine Calf Extensions", "Sets": 4, "Target Reps": "15", "Weight Input": [50, 45, 40], "Strategy": "linear", "Rounding": 5, "Superset Group": "C"},
        {"Day Name": "Lower Body", "Exercise": "Weighted Back Extensions", "Sets": 3, "Target Reps": "15", "Weight Input": [10, 5, 5], "Strategy": "linear", "Rounding": 5, "Superset Group": "C"},
        
        # Abs (machine-based, not static)
        {"Day Name": "Lower Body", "Exercise": "Abdominal Crunch Machine", "Sets": 3, "Target Reps": "15", "Weight Input": [50, 45, 40], "Strategy": "linear", "Rounding": 5, "Superset Group": None},
    ],

    4: [ # Day 4: Chest & Back (Volume)
        {"Day Name": "Chest & Back", "Exercise": "Flat Dumbbell Bench Press", "Sets": 3, "Target Reps": "10", "Weight Input": [26, 26, 22], "Strategy": "linear", "Rounding": 2, "Superset Group": None},
        {"Day Name": "Chest & Back", "Exercise": "Incline Dumbbell Bench Press", "Sets": 3, "Target Reps": "12", "Weight Input": [22, 20, 20], "Strategy": "linear", "Rounding": 2, "Superset Group": None},
        {"Day Name": "Chest & Back", "Exercise": "Machine Open Row", "Sets": 3, "Target Reps": "12", "Weight Input": [47, 42, 37], "Strategy": "linear", "Rounding": 5, "Superset Group": None},
        {"Day Name": "Chest & Back", "Exercise": "Closed Grip Lat Pulldown", "Sets": 3, "Target Reps": "12", "Weight Input": [50, 45, 40], "Strategy": "linear", "Rounding": 2.5, "Superset Group": None},
        
        # Superset A (Bodyweight)
        {"Day Name": "Chest & Back", "Exercise": "Push Ups", "Sets": 3, "Target Reps": "Failure", "Weight Input": [0, 0, 0], "Strategy": "linear", "Rounding": 0, "Superset Group": "A"},
        {"Day Name": "Chest & Back", "Exercise": "Pull Ups", "Sets": 3, "Target Reps": "Failure", "Weight Input": [0, 0, 0], "Strategy": "linear", "Rounding": 0, "Superset Group": "A"},
    ],

    5: [ # Day 5: Arms (Pump)
        # Superset A — synced with Day 1 anchor weights
        {"Day Name": "Arms", "Exercise": "Overhead Cable Tricep Ext", "Sets": 4, "Target Reps": "12", "Weight Input": [65, 60, 55, 50], "Strategy": "linear", "Rounding": 2.5, "Superset Group": "A"},
        {"Day Name": "Arms", "Exercise": "Open Cable Curls", "Sets": 4, "Target Reps": "12", "Weight Input": [20, 20, 17.5, 15], "Strategy": "linear", "Rounding": 2.5, "Superset Group": "A"},
        
        # Superset B — Tricep Rope uses same 20kg anchor as Day 1 Pushdowns
        {"Day Name": "Arms", "Exercise": "Tricep Rope Pulldowns", "Sets": 4, "Target Reps": "15", "Weight Input": [85, 75, 70, 65], "Strategy": "linear", "Rounding": 2.5, "Superset Group": "B"},
        {"Day Name": "Arms", "Exercise": "DB Hammer Curls", "Sets": 4, "Target Reps": "12", "Weight Input": [18, 18, 16, 16], "Strategy": "linear", "Rounding": 2, "Superset Group": "B"},
        
        # Superset C — small muscle, explicit arrays
        {"Day Name": "Arms", "Exercise": "DB Lateral Raises", "Sets": 3, "Target Reps": "20", "Weight Input": [8, 7, 6], "Strategy": "linear", "Rounding": 1, "Superset Group": "C"},
        {"Day Name": "Arms", "Exercise": "Cable Face Pulls", "Sets": 3, "Target Reps": "20", "Weight Input": [55, 50, 45], "Strategy": "linear", "Rounding": 2.5, "Superset Group": "C"},
        
        # Superset D — small muscle, explicit arrays (synced w/ Day 1 Lateral Cable & Day 2 Reverse Flyes)
        {"Day Name": "Arms", "Exercise": "Cable Lateral Raises", "Sets": 3, "Target Reps": "15", "Weight Input": [3.75, 2.5, 2.5], "Strategy": "linear", "Rounding": 1.25, "Superset Group": "D"},
        {"Day Name": "Arms", "Exercise": "Reverse Cable Flyes", "Sets": 3, "Target Reps": "15", "Weight Input": [3.75, 2.5, 2.5], "Strategy": "linear", "Rounding": 1.25, "Superset Group": "D"},
    ]
}

# ---------------------------------------------------------
# 3. THE COMPILER (Merges Lifts + Abs + Calculates Drops)
# ---------------------------------------------------------
final_data = []

for day_num in range(1, 6): # Loop Days 1 to 5
    todays_lifts = daily_workouts.get(day_num, [])
    
    if not todays_lifts: continue
        
    current_order = 1
    day_name = todays_lifts[0]["Day Name"]
    
    # 1. Process Main Lifts
    for lift in todays_lifts:
        row = lift.copy()
        row["Day"] = day_num
        row["Order"] = current_order
        
        # --- THE CORE LOGIC ---
        # Convert the single "Weight Input" into the JSON Array String.
        # If Weight Input is already a list, strict_list passes it through as-is.
        # This allows small-muscle exercises to define explicit arrays
        # (e.g., [10, 10, 8]) that bypass aggressive auto-drop math.
        if lift.get("Strategy") == "periodized_bench":
            # Bench uses uniform weight across all sets: [90, 90, 90, 90, 90]
            row["target_weight_json"] = uniform_list(
                lift["Weight Input"],
                lift["Sets"]
            )
        else:
            row["target_weight_json"] = strict_list(
                lift["Weight Input"], 
                lift["Sets"], 
                lift.get("Rounding", 2.5)
            )
        
        # Remove the raw input so the Excel is clean
        del row["Weight Input"]
        
        final_data.append(row)
        current_order += 1
        
    # 2. Append the Abs Routine (Skipping Day 3 as per your logic)
    if day_num != 3:
        for abs_ex in abs_routine:
            row = abs_ex.copy()
            row["Day"] = day_num
            row["Day Name"] = day_name
            row["Order"] = current_order
            
            # Abs are bodyweight (0), so we generate [0, 0, 0]
            row["target_weight_json"] = strict_list(0, row["Sets"], 0)
            
            # Remove keys that might not exist in abs_routine to be safe
            if "Baseline Weight (kg)" in row: del row["Baseline Weight (kg)"]
            if "Weight Input" in row: del row["Weight Input"]

            final_data.append(row)
            current_order += 1

# ---------------------------------------------------------
# 4. EXPORT
# ---------------------------------------------------------
df = pd.DataFrame(final_data)

# Reorder for clarity
cols = ["Day", "Day Name", "Order", "Exercise", "Sets", "Target Reps", "target_weight_json", "Strategy", "Rounding", "Superset Group"]
df = df[cols]

df.to_excel("gym_routine_master.xlsx", index=False)
print("gym_routine_master.xlsx created successfully with calculated drop sets.")