# Arbiter

Arbiter is a data analysis tool made by SimPPL. This repository contains all the backend code and all the config files for Arbiter.

Arbiter backend has only 2 components: API and Database. Our API searches through the data of telegram and generate analytics on the basis of semantic searching.

> Arbiter is in it's MVP stage as of now.

## Index

- [API](#api)
- [Python](#python)

## API

Arbiter's API purpose is to provide data for creating dashboard on the frontend and act as an intemdiary for searching and collecting data from the database.

We are using FastAPI for creating the API. To run API in the development mode

```shell
$ fastapi dev api/server.py
```

## Python

Python Versions

```shell
pyenv virtualenv 3.12.6 venv
pyenv activate venv
```
