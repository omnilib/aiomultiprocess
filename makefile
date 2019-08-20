build:
	python3 setup.py build

dev:
	python3 setup.py develop

setup:
	python3 -m pip install -Ur requirements-dev.txt

venv:
	python3 -m venv .venv
	source .venv/bin/activate && make setup dev
	echo 'run `source .venv/bin/activate` to use virtualenv'

release: lint test clean
	python3 setup.py sdist
	python3 -m twine upload dist/*

black:
	python3 -m isort --apply --recursive aiomultiprocess setup.py
	python3 -m black aiomultiprocess

lint:
	python3 -m mypy aiomultiprocess
	python3 -m pylint --rcfile .pylint aiomultiprocess setup.py
	python3 -m isort --diff --recursive aiomultiprocess setup.py
	python3 -m black --check aiomultiprocess

test:
	python3 -m coverage run --concurrency=multiprocessing -m aiomultiprocess.tests
	python3 -m coverage combine
	python3 -m coverage report

clean:
	rm -rf build dist README MANIFEST aiomultiprocess.egg-info
