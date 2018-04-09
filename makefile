build:
	python3 setup.py build

dev:
	python3 setup.py develop

release: lint test clean
	python3 setup.py sdist
	python3 -m twine upload dist/*

setup:
	pip3 install -U mypy pylint twine
	pip3 install black

black:
	black aiomultiprocess tests

lint:
	black --check aiomultiprocess tests
	pylint --rcfile .pylint aiomultiprocess setup.py
	mypy --ignore-missing-imports --python-version 3.6 .

test:
	python3 -m unittest tests

clean:
	rm -rf build dist README MANIFEST aiomultiprocess.egg-info
