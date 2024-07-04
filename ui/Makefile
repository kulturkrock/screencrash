
.PHONY: default init build watch serve dev

default: build

node_modules: package.json package-lock.json
	npm ci

init: node_modules

build: node_modules
	npm run build

watch: node_modules
	npm run watch

serve: node_modules
	npm run serve

dev: node_modules
	npm run dev
