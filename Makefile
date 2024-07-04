.PHONY: dev

dev_core:
	make -C "core" dev

dev_ui:
	make -C "ui" dev
	
dev_media:
	make -C "components/media" dev

dev_inventory:
	make -C "components/inventory" dev

dev: dev_core dev_ui dev_media