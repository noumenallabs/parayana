# Vāgdhenu Goṣṭhī Studio — Unified Monorepo Automation
.PHONY: setup dev verify-all verify-backend verify-frontend clean

PYTHON ?= backend/.venv/bin/python
ifeq ($(OS),Windows_NT)
    PYTHON = backend/.venv/Scripts/python.exe
endif

setup:
	@echo "=== Setting up Vāgdhenu Goṣṭhī Studio ==="
ifeq ($(OS),Windows_NT)
	@echo "Detected Windows. Setting up Python venv..."
	python -m venv backend/.venv || uv venv --python 3.10 backend/.venv
	$(PYTHON) -m pip install -r backend/requirements.txt
	$(PYTHON) backend/scripts/generate_acoustics.py
	$(PYTHON) backend/scripts/seed_default_pandits.py
else
	chmod +x backend/scripts/setup_m3.sh
	./backend/scripts/setup_m3.sh
	$(PYTHON) backend/scripts/seed_default_pandits.py
endif
	cd frontend && npm install
	@echo "=== Setup Complete! ==="

verify-all: verify-backend verify-frontend
	@echo "\n=============================================="
	@echo "  ALL VERIFICATION SUITES (US-01 to US-10) PASSED"
	@echo "==============================================\n"

verify-backend:
	@echo "--- Running Verification Suites (US-01 through US-08) ---"
	$(PYTHON) backend/tests/verify_us01_env.py
	$(PYTHON) backend/tests/verify_us02_db.py
	$(PYTHON) backend/tests/verify_us03_parser.py
	$(PYTHON) backend/tests/verify_us04_voice_forge.py
	$(PYTHON) backend/tests/verify_us05_chant_worker.py
	$(PYTHON) backend/tests/verify_us06_vc_worker.py
	$(PYTHON) backend/tests/verify_us07_mixer.py
	$(PYTHON) backend/tests/verify_us08_api.py

verify-frontend:
	@echo "--- Verifying Frontend Typecheck and Production Build (US-09 & US-10) ---"
	cd frontend && npm run typecheck
	cd frontend && npm run build

dev:
	@echo "Starting Vāgdhenu Goṣṭhī Studio (Backend & Frontend)..."
ifeq ($(shell uname -s 2>/dev/null),Darwin)
	@echo "Running under macOS caffeinate -i to prevent idle sleep throttling..."
	caffeinate -i bash -c "trap 'kill 0' SIGINT; (cd backend && $(PYTHON) -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload) & (cd frontend && npm run dev) & wait"
else
	powershell -Command "Start-Process -FilePath '$(PYTHON)' -ArgumentList '-m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload'; Set-Location frontend; npm run dev"
endif

clean:
	rm -rf frontend/.next
	rm -rf backend/storage/test_*
	find . -type d -name "__pycache__" -exec rm -rf {} +
