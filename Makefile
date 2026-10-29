.PHONY: setup build start test evaluate lint diagrams
setup:
	python3 tools/setup.py
build:
	python3 tools/run.py build
start:
	python3 tools/run.py start
test:
	python3 tools/run.py test
evaluate:
	python3 tools/run.py evaluate
lint:
	.venv/bin/ruff check src tests tools
diagrams:
	python3 tools/render_diagrams.py
