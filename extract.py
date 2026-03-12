import json
import glob

exercises = {}
for file in glob.glob('/home/sterry/Desktop/GYM_AI/data/workouts/*.json'):
    with open(file) as f:
        data = json.load(f)
        for ex in data.get('exercises', []):
            if ex['exercise_id'] not in exercises:
                exercises[ex['exercise_id']] = ex['exercise']

print(json.dumps(exercises, indent=2))
