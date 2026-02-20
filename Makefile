.PHONY: clean build reset dev-backend dev-frontend update-week log-weight stop

# Preserves the /data lake (CSVs)
clean:
	rm -f backend/gym.db backend/gym_routine_master.xlsx
	@echo "✅ Cleaned DB and Excel. Metrics CSVs preserved."

build:
	mkdir -p data/workouts data/metrics
	cd backend && python3 generate_routine.py && python3 init_db.py
	@echo "✅ Database is fresh."

# Updated reset to use 8000 for the backend consistency
reset: stop clean build
	@echo "🔄 Auto-fetching Renpho metrics..."
	-cd backend && python3 fetch_renpho.py || echo "Warning: Renpho fetch failed."
	@echo "🚀 Starting servers..."
	# Backend starts on port 8000 (default in your main.py)
	cd backend && python3 main.py & 
	# Vite will now use your config's 'host: true' automatically
	cd frontend && npm run dev -- --host

stop:
	@echo "🛑 Killing existing servers..."
	-pkill -f "python3 main.py" || true
	-lsof -t -i:8000 | xargs kill -9 2>/dev/null || true
	-lsof -t -i:5173 | xargs kill -9 2>/dev/null || true

log-weight:
	cd backend && python3 fetch_renpho.py