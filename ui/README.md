# screencrash-ui

Directory for the UI of Screencrash (also known as Skärmkrock)

- [screencrash-ui](#screencrash-ui)
  - [Dependencies](#Dependencies)
  - [Setup and Commands](#Setup-and-Commands)
  - [Files and Folders](#Files-and-Folders)

## Dependencies

The primary dependency for this repository is [Node.js](https://nodejs.org/) 22.13.0 which needs to be installed and accessible. (Downloads can be found [here](https://nodejs.org/dist/v22.13.0/), in case the previous link leads to a newer version.)
To manage Node versions on Mac or Linux, you can also use [NVM](https://github.com/nvm-sh/nvm).

In particular, whatever editor or command line you wish to use needs to be able to run `npm`, which will manage the code and development dependencies.

An optional dependency on GNU Make exists, in that a simple `Makefile` is provided, but the commands all delegate to `npm` (see next section).

## Setup and Commands

The following commands are available, and should be run from the repository root folder (same folder as the `Makefile` and `package.json`).

When using `make`, installing of dependencies will be done automatically and `make init` should not need to be run manually. However, when only using `npm` then `npm ci` must be run first in order to install the dependencies for the other commands.

| Using `make`                 | Using `npm`                          |                                                                                        |
| ---------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------- |
| `make`                       |                                      | Running make without arguments is equivalent to `make build`                           |
| <code>make&nbsp;init</code>  | <code>npm&nbsp;ci</code>             | Install dependencies                                                                   |
| <code>make&nbsp;build</code> | <code>npm&nbsp;run&nbsp;build</code> | Build the project                                                                      |
| <code>make&nbsp;dev</code>   | <code>npm&nbsp;run&nbsp;dev</code>   | Run in dev mode, with automatic rebuild on changes and automatic reload in the browser |

The easiest way to get started should be to run `make dev`, which will

1.  install dependencies if needed,
2.  build the project,
3.  start a server for the project,
4.  open a web browser to the project,
5.  and rebuild and reload as needed when editing source files.
