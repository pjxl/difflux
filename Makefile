.PHONY: help setup install test _python311 _pipx

VENV := .venv

help:
	@printf 'Targets:\n'
	@printf '  setup    Install Python 3.11, pipx, and wire difflux onto PATH\n'
	@printf '  install  Reinstall difflux (picks up local code changes)\n'
	@printf '  test     Run the test suite\n'

setup: _python311 _pipx install
	@echo "Done. Run: difflux"
	@echo "(If not found, restart your shell or: export PATH=\"\$$HOME/.local/bin:\$$PATH\")"

_python311:
	@if ! command -v python3.11 >/dev/null 2>&1; then \
		echo "Installing Python 3.11..."; \
		sudo apt-get install -y software-properties-common; \
		sudo add-apt-repository -y ppa:deadsnakes/python; \
		sudo apt-get update -q; \
		sudo apt-get install -y python3.11 python3.11-venv; \
	elif ! python3.11 -m venv --help >/dev/null 2>&1; then \
		echo "Installing python3.11-venv..."; \
		sudo apt-get install -y python3.11-venv; \
	else \
		echo "python3.11 already available: $$(python3.11 --version)"; \
	fi

_pipx:
	@if command -v pipx >/dev/null 2>&1; then \
		echo "pipx already available: $$(pipx --version)"; \
	else \
		echo "Installing pipx..."; \
		sudo apt-get install -y pipx; \
		pipx ensurepath; \
	fi

install:
	pipx install -e . --python python3.11 --force

$(VENV): _python311
	python3.11 -m venv $(VENV)
	$(VENV)/bin/pip install -e ".[dev]"

test: $(VENV)
	$(VENV)/bin/pytest tests/
