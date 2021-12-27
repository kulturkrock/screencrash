.PHONY: dev

dev:
	sh -c \
	'CORE=localhost:8001 make -C screencrash-ui dev & \
	make -C screencrash-core dev & \
	CORE=localhost:8001 make -C screencrash-components dev & \
	wait'