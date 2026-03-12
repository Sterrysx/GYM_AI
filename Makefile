.PHONY: start reset nuke-db stop dev-backend dev-frontend log-weight

# 1. THE DAILY COMMAND: Safely boots everything without deleting data
start: stop
	@echo "🚀 Starting servers safely (Database Preserved)..."
	-cd backend && python3 fetch_renpho.py || echo "Renpho fetch skipped."
	cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 &
	cd frontend && npm run dev -- --host

# 2. SAFE RESET: Rebuilds plan but preserves the actual .db file
reset: stop
	@echo "🔄 Rebuilding routine blueprint (Preserving History)..."
	mkdir -p data/workouts data/metrics
	-cd backend && python3 generate_baseline.py || echo "Baseline preserved/skipped."
	@echo "✅ Servers starting..."
	cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 &
	cd frontend && npm run dev -- --host

# 3. DESTRUCTIVE WIPE: Only use if you want to lose ALL progress
nuke-db: stop
	@echo "☢️  WARNING: Wiping SQLite Database and Excel Blueprint..."
	rm -f backend/gym.db backend/gym_routine_master.xlsx
	@echo "✅ Cleaned DB and Excel. Metrics CSVs preserved. Run 'make reset' to rebuild."

stop:
	@echo "🛑 Killing existing servers on 8000 and 5173..."
	-pkill -f "uvicorn" || true
	-lsof -t -i:8000 | xargs kill -9 2>/dev/null || true
	-lsof -t -i:5173 | xargs kill -9 2>/dev/null || true

log-weight:
	cd backend && python3 fetch_renpho.py