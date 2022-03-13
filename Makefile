.PHONY: dev

dev_core:
	make -C "screencrash-core" dev

dev_ui:
	make -C "screencrash-ui" dev
	
dev_media:
	make -C "screencrash-components/media" dev

dev_inventory:
	make -C "screencrash-components/inventory" dev

dev: dev_core dev_ui dev_media dev_inventory