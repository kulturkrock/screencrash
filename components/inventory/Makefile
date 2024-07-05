
.PHONY: default init dev

default: dev

node_modules: package.json package-lock.json
	npm ci

dev: node_modules
	npm run dev
