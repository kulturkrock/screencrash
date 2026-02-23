.PHONY: default init dev test

default: dev

init:
	pdm install

# This reloads the app when Python files change.
dev: init
	pdm run watchmedo auto-restart \
		--patterns="*.py" \
		--recursive \
		python -- src/main.py

# This won't reload the app when Python files change.
# (You can try this if you can't get "make dev" to work.)
test: init
	pdm run -- src/main.py
