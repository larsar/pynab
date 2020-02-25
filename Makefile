#!/usr/bin/env make

install:
	pip install -r requirements.txt

freeze:
	pip freeze > requirements.txt

venv:
	virtualenv -p python3 venv

