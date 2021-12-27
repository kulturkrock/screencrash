.PHONY: dev

dev:
	sh -c \
	'make -C screencrash-ui dev & \
	make -C screencrash-core dev & \
	make -C screencrash-components dev & \
	wait'