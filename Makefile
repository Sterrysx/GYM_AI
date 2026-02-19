.PHONY: clean build reset dev-backend dev-frontend update-week log-weight

# 1. Wipes the old database and Excel file
clean:
	rm -f backend/gym.db backend/gym_routine_master.xlsx
	@echo "Cleaned old database and routine files."

# 2. Re-generates the Excel blueprint and seeds the fresh Database
#    Also ensures the /data lake directories exist.
build:
	mkdir -p data/workouts data/metrics
	cd backend && python generate_routine.py && python init_db.py
	@echo "Build complete. Database is fresh. Data lake dirs ready."

# 3. The "Do Everything" command — clean, build, then launch both servers
reset: clean build
	@echo "Starting backend (background) and frontend..."
	cd backend && python main.py &
	cd frontend && npm run dev

# 4. Start the backend API server
dev-backend:
	cd backend && python main.py

# 5. Start the Vite frontend dev server
dev-frontend:
	cd frontend && npm run dev

# 6. Manually trigger the weekly update script
update-week:
	cd backend && python weekly_coach.py

# 7. Log a Renpho body‐composition reading
log-weight:
	cd backend && python fetch_renpho.py