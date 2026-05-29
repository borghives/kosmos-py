.PHONY: all sync update tag clean commit stage submit test

all: 
	@echo "Please specify a command: make init, make update, etc."

sync:
	git pull origin main; git pull

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