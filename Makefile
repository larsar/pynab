#!/usr/bin/env make

install:
	pip install -r requirements.txt

freeze:
	pip freeze > requirements.txt

venv:
	python3 -m venv venv

