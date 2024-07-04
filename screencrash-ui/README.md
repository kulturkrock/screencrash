# screencrash-ui

Repository for the UI of Screencrash (also known as Skärmkrock)

- [screencrash-ui](#screencrash-ui)
  - [Dependencies](#Dependencies)
  - [Setup and Commands](#Setup-and-Commands)
  - [Files and Folders](#Files-and-Folders)

## Dependencies

The primary dependency for this repository is [Node.js](https://nodejs.org/) 10.16.0 which needs to be installed and accessible. (Downloads can be found [here](https://nodejs.org/dist/v10.16.0/), in case the previous link leads to a newer version.)
To manage Node versions on Mac or Linux, you can also use [NVM](https://github.com/nvm-sh/nvm).

In particular, whatever editor or command line you wish to use needs to be able to run `npm`, which will manage the code and development dependencies.

An optional dependency on GNU Make exists, in that a simple `Makefile` is provided, but the commands all delegate to `npm` (see next section).

## Setup and Commands

The following commands are available, and should be run from the repository root folder (same folder as the `Makefile` and `package.json`).

When using `make`, installing of dependencies will be done automatically and `make init` should not need to be run manually. However, when only using `npm` then `npm ci` must be run first in order to install the dependencies for the other commands.

| Using `make`                 | Using `npm`                          |                                                                                                                                              |
| ---------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `make`                       |                                      | Running make without arguments is equivalent to `make build`                                                                                 |
| <code>make&nbsp;init</code>  | <code>npm&nbsp;ci</code>             | Install dependencies                                                                                                                         |
| <code>make&nbsp;build</code> | <code>npm&nbsp;run&nbsp;build</code> | Build the project                                                                                                                            |
| <code>make&nbsp;watch</code> | <code>npm&nbsp;run&nbsp;watch</code> | Build, and then watch for changes in the source and rebuild as needed                                                                        |
| <code>make&nbsp;serve</code> | <code>npm&nbsp;run&nbsp;serve</code> | Start a [browser-sync](https://www.browsersync.io/) server and open a new browser tab or window to it using the system's default web browser |
| <code>make&nbsp;dev</code>   | <code>npm&nbsp;run&nbsp;dev</code>   | Run `make watch` and `make serve` in parallel, providing automatic rebuild on changes and automatic reload in the browser                    |

The easiest way to get started should be to run `make dev`, which will

1.  install dependencies if needed,
2.  build the project,
3.  start a server for the project,
4.  open a web browser to the project,
5.  and rebuild and reload as needed when editing source files.

## Files and Folders

| Path                     |                                                                                                                                                                  |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `README.md`              | This file. Hi!                                                                                                                                                   |
| `LICENSE`                | License text.                                                                                                                                                    |
| `Makefile`               | Makefile, containing the commands described above.                                                                                                               |
| `package.json`           | Node.js package file, describing the `npm` commands above and all direct dependencies.                                                                           |
| `package-lock.json`      | Used by `npm` to specify the exact versions of all dependencies. No need to edit this manually.                                                                  |
| `tsconfig.json`          | TypeScript configuration for the project.                                                                                                                        |
| `webpack.config.js`      | Configuration for `webpack` that describes how to build the project.                                                                                             |
| `browser-sync.config.js` | Configuration for `browser-sync` which describes how to serve the project.                                                                                       |
| `src/`                   | Source code, compiled by `webpack` using the build commands described above.                                                                                     |
| `src/tsx/main.tsx`       | The main entry point of the project.                                                                                                                             |
| `dist/`                  | "Distribution," i.e., where the project is built to and served from. This contains static files (in particular, `index.html`) that are not managed by `webpack`. |
| `dist/webpack/`          | Where `webpack` is configured to put all compilation output, and is ignored by `git`. Deleting this folder is equivalent to cleaning the build.                  |
| `node_modules`           | Where `npm` puts dependencies it installs, and is ignored by `git`.                                                                                              |
| `sample_data`            | Where any sample data used for faking Core should be placed.                                                                                                     |
