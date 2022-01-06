.PHONY: dev

dev_core:
	make -C "screencrash-core" dev

dev_ui:
	make -C "screencrash-ui" dev

dev_audio:
	make -C "screencrash-components/audio" dev
	
dev_screen:
	make -C "screencrash-components/screen" dev

dev_components: dev_audio dev_screen

dev: dev_core dev_ui dev_audio dev_screen