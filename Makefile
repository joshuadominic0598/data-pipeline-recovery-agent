.PHONY: setup build start test evaluate lint diagrams
setup:
	python3 scripts/setup.py
build:
	python3 scripts/run.py build
start:
	python3 scripts/run.py start
test:
	python3 scripts/run.py test
evaluate:
	python3 scripts/run.py evaluate
lint:
	.venv/bin/ruff check backend tests scripts
diagrams:
	python3 scripts/render_diagrams.py
