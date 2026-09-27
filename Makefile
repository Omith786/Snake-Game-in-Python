PYTHON ?= python3
VENV   := .venv
BIN    := $(VENV)/bin
HEADLESS := SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy

.PHONY: install run test screenshot clean

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)

install: $(BIN)/python
	$(BIN)/pip install -r requirements-dev.txt

run:
	$(BIN)/python -m snake

test:
	$(HEADLESS) $(BIN)/python -m pytest -q

screenshot:
	$(HEADLESS) $(BIN)/python scripts/screenshot.py

clean:
	find . -path ./$(VENV) -prune -o -name __pycache__ -type d -exec rm -rf {} +
	rm -rf .pytest_cache
