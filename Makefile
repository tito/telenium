.PHONY: release

release:
	rm -rf dist build *.egg-info
	python setup.py sdist
	python setup.py bdist_wheel
	twine upload dist/*
