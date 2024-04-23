PKG:=aiomultiprocess
EXTRAS:=dev,docs

.venv:
	python -m venv .venv
	source .venv/bin/activate && make install
	echo 'run `source .venv/bin/activate` to use virtualenv'
 
venv: .venv

install:
	python -m pip install -U pip
	python -m pip install -Ue .[$(EXTRAS)]

release: lint test clean
	python -m flit publish

format:
	python -m usort format $(PKG)
	python -m black $(PKG)

lint:
	python -m flake8 $(PKG)
	python -m usort check $(PKG)
	python -m black --check $(PKG)

test:
	python -m coverage run -m aiomultiprocess.tests
	python -m coverage combine
	python -m coverage report
	python -m mypy $(PKG)

perf:
	export PERF_TESTS=1 && make test

.PHONY: html
html: .venv README.md docs/* docs/*/* aiomultiprocess/*
	source .venv/bin/activate && sphinx-build -ab html docs html

clean:
	rm -rf build dist html README MANIFEST aiomultiprocess.egg-info

distclean: clean
	rm -rf .venv
