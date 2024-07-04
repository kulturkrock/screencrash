# Audio component

Project for the Audio Component in Screencrash (also known as Skärmkrock)

- [Top of page](#audio-component)
  - [Dependencies](#Dependencies)
  - [Setup and Commands](#Setup-and-Commands)
  - [Files and Folders](#Files-and-Folders)
  - [Running manually](#Running-manually)

## Dependencies

You need [Pipenv](https://github.com/pypa/pipenv). The easiest way to install it is to get `pip`
and run `pip install --user pipenv`. If you get `pipenv: command not found` you might need to
log out and in again.

## Setup and Commands

The following commands are available:

| Command                     | Effect                                                                        |
| --------------------------- | ----------------------------------------------------------------------------- |
| `make`                      | Run both `init` and `dev`                                                     |
| <code>make&nbsp;init</code> | Install dependencies                                                          |
| <code>make&nbsp;dev</code>  | Run Audio Component in development mode, with automatic reload on file change |

## Files and Folders

| Path           |                                                                                  |
| -------------- | -------------------------------------------------------------------------------- |
| `README.md`    | This file. Hi!                                                                   |
| `Makefile`     | Makefile, containing the commands described above.                               |
| `Pipfile`      | Describes the dependencies                                                       |
| `Pipfile.lock` | Used by `pipenv` to specify the exact versions of dependencies. Don't edit this. |
| `res/`         | The location to place dev resources for use in development                       |
| `src/`         | Source code.                                                                     |
| `src/main.py`  | The main entry point of the project.                                             |

## Running manually

Run the project with ```python main.py``` from the audio folder. Possible arguments are the following:
| Parameter         | Type   | Default value | Description                                            |
| ----------------- | ------ | ------------- | ------------------------------------------------------ |
| --enable-ws-debug |        | False         | If set, enables websocket debug information            |
| --no-reconnect    |        | False         | If set, disables the reconnect feature                 |
| --reconnect-time  | int    | 3000          | Time (in ms) from a disconnect to reconnection attempt |


## Visual Studio Code configuration
There is a run configuration available for the audio module. Just open the entire repo folder in Visual studio code and
it should automagically know how to run etc. Yay!
