build:
	python3 setup.py build

dev:
	python3 setup.py develop

release: lint test clean
	python3 setup.py sdist
	python3 -m twine upload dist/*

setup:
	pip3 install -U black mypy pylint twine

black:
	black aiomultiprocess tests

lint:
	mypy --ignore-missing-imports .
	pylint --rcfile .pylint aiomultiprocess setup.py
	black --check aiomultiprocess tests

test:
	python3 -m unittest tests

clean:
	rm -rf build dist README MANIFEST aiomultiprocess.egg-info
