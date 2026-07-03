.ONESHELL:
VENV := .venv
PY := $(VENV)/bin/python

venv:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip setuptools wheel

venv-system:
	# Recreate the venv using system site-packages so system libraries like gi are importable
	rm -rf $(VENV)
	python3 -m venv --system-site-packages $(VENV)
	$(PY) -m pip install --upgrade pip setuptools wheel

install-dev: venv
	$(PY) -m pip install -r requirements-dev.txt

test:
	# Run tests; set MARKER to run only tests with a given pytest marker
	if [ -n "$(MARKER)" ]; then
		if [ -x "$(PY)" ]; then
			$(PY) -m pytest -q -m "$(MARKER)"
		else
			python3 -m pytest -q -m "$(MARKER)"
		fi
	else
		if [ -x "$(PY)" ]; then
			$(PY) -m pytest -q
		else
			python3 -m pytest -q
		fi
	fi

test-ui:
	$(MAKE) test MARKER=ui

test-gtk:
	$(MAKE) test MARKER=gtk

clean:
	rm -rf $(VENV) .pytest_cache __pycache__
