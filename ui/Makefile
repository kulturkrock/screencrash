
.PHONY: default init build dev

default: build

node_modules: package.json package-lock.json
	npm ci

init: node_modules

build: node_modules
	npm run build

dev: node_modules
	npm run dev
