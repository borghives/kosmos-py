.PHONY: all sync update tag clean commit stage submit

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
	@echo "coming soon..."

submit: sync update test stage commit 