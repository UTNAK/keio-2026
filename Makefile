.PHONY: build up down logs kernelspec shell samples opencode-auth doctor

samples:
	@mkdir -p workspace/samples
	@if [ -d workspace/samples/OpenSysML/.git ]; then \
		echo "OpenSysML samples already present; leaving checkout unchanged"; \
	elif [ -e workspace/samples/OpenSysML ]; then \
		echo "workspace/samples/OpenSysML exists but is not a Git checkout; refusing to overwrite it" >&2; \
		exit 1; \
	else \
		git clone --depth 1 \
		https://github.com/Open-MBEE/OpenSysML.git \
			workspace/samples/OpenSysML; \
	fi

build:
	docker compose build jupyter

up:
	docker compose up --remove-orphans jupyter

down:
	docker compose down --remove-orphans

logs:
	docker compose logs --follow jupyter

opencode-auth:
	docker compose exec --user keio jupyter opencode auth login

doctor:
	docker compose exec -T --user keio jupyter python /opt/course/opencode/check_opencode_integration.py

kernelspec:
	docker compose run --rm --no-deps jupyter jupyter kernelspec list

shell:
	docker compose run --rm --no-deps --entrypoint bash jupyter
