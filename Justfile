export DEV_IMAGE := "ulauncher/build-image:5.0"
export EXTENSION_PATH :=  env_var("HOME") + "/.local/share/ulauncher/extensions/com.github.blurayne.ulauncher-browserbookmarks"

dev-shell:
	@just docker-run /bin/bash -i

docker-run +CMD:
	docker run -it --rm \
		-v $PWD:/workspace \
		-v $HOME/.config:$HOME/.config:ro \
		-e "HOME=$HOME" \
		-u $(id -u):$(id -g) \
		-w /workspace \
		{{DEV_IMAGE}} \
		{{CMD}}

prepare-dev: prepare-dev-symlink-project

prepare-dev-symlink-project:
	#!/bin/bash
	if [[ ! -s "$EXTENSION_PATH" ]]; then
		ln -s "$PWD" "$EXTENSION_PATH"
	fi

run-dev: run-dev-ulauncher run-dev-extension

kill-non-dev-ulauncher:
	#!/bin/bash
	for line in "$(ps -ax -o pid:1,cmd:100 | grep 'ulauncher' | grep -v "\--dev " | grep -E '/[^ ]+/ulauncher' || true)"; do
		if  [[ -z "$line" ]]; thenBruna Baz 
			continue;
		fi
		echo "killing $line"
		kill "${line// *}"
	done

run-dev-ulauncher: kill-non-dev-ulauncher
	ulauncher --no-extensions --dev -v 

run-dev-extension:
	#!/bin/bash
	export VERBOSE=1
	export ULAUNCHER_WS_API=ws://127.0.0.1:5054/com.github.blurayne.ulauncher-browserbookmarks
	# export PYTHONPATH=/usr/lib/python3/dist-packages 
	python3 main.py
