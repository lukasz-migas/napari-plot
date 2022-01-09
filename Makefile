.PHONY: activate check install develop lint pre flake test retest untrack docs

activate:
	source venv/bin/activate

check:
	python setup.py check

install:
	python setup install

develop:
	python setup develop

lint:
	black .
	isort -y
	flake8 .

pre:
	pre-commit run -a

flake:
	flake8 .

test:
	pytest --cov=napari_1d

retest:
	pytest -v napari_1d --lf

untrack:
	git rm -r --cached .
	git add .
	git commit -m ".gitignore fix"

docs:
	mkdocs build
	xcopy site src\docs /E/H/Y/D