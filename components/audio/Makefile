.PHONY: default init dev

default: init dev

init:
	pdm install

dev: init
	pdm run watchmedo auto-restart \
		--patterns="*.py" \
		--recursive \
		python -- src/main.py