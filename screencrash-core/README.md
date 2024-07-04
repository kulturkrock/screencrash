# screencrash-core

Repository for the core component of Screencrash (also known as Skärmkrock)

- [screencrash-core](#screencrash-core)
  - [Dependencies](#Dependencies)
  - [Setup and Commands](#Setup-and-Commands)
  - [Files and Folders](#Files-and-Folders)

## Dependencies

You need [Pipenv](https://github.com/pypa/pipenv). The easiest way to install it is to get `pip`
and run `pip install --user pipenv`. If you get `pipenv: command not found` you might need to
log out and in again.

## Setup and Commands

Before starting, download all files from `Kulturkrock/Projekt/Skärmkrock/Utvecklingsdata` on
the Drive and put them under `resources`.

The following commands are available:

| Command                     | Effect                                                             |
| --------------------------- | ------------------------------------------------------------------ |
| `make`                      | Run both `init` and `dev`                                          |
| <code>make&nbsp;init</code> | Install dependencies                                               |
| <code>make&nbsp;dev</code>  | Run Core in development mode, with automatic reload on file change |

## Environment variables

You can configure Core with the following environment variables:

| Variable                                 | Effect                                          |                 |
| ---------------------------------------- | ----------------------------------------------- | --------------- |
| `OPUS`                                   | Which opus file (under `resources`) to use      | `dev_opus.yaml` |
| `SCREENCRASH_SYNC_ASSETS`                | Whether to sync assets when components connect. | `true`          |
| `SCREENCRASH_EXIT_ON_VALIDATION_FAILURE` | Whether to exit if the opus fails to validate   | `true`          |

## Files and Folders

| Path           |                                                                                  |
| -------------- | -------------------------------------------------------------------------------- |
| `README.md`    | This file. Hi!                                                                   |
| `LICENSE`      | License text.                                                                    |
| `Makefile`     | Makefile, containing the commands described above.                               |
| `Pipfile`      | Describes the dependencies                                                       |
| `Pipfile.lock` | Used by `pipenv` to specify the exact versions of dependencies. Don't edit this. |
| `src/`         | Source code.                                                                     |
| `src/main.py`  | The main entry point of the project.                                             |
| `resources`    | The location to place resources for use in development                           |
