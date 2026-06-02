.PHONY: all sync update tag clean commit stage submit test

all: 
	@echo "Please specify a command: make init, make update, etc."

init:
	uv venv

sync:
	git pull origin main; git pull
	uv sync

update:
	uv sync --upgrade

clean:
	rm -f tag

stage:
	git add .

commit:
	gca && git push

test:
	@uv run pytest

submit: sync update test stage commit 