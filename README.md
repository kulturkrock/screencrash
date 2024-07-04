# Screencrash

Main repository for the Screencrash project (also known as Skärmkrock).

## Setup

After cloning this repo, run `git submodule update --init` to initialize the
sub-repos. Then follow the setup instructions in the README of each sub-repo.

## Starting Screencrash

To start the UI, Core and Components in dev mode, run `make -j3 dev`. To run individual parts, use:

| Command                 | Result                                                                    |
| ----------------------- | ------------------------------------------------------------------------- |
| make -j4 dev            | Run all parts in parallell. Log output will be to the same terminal.      |
| make dev_core           | Run core                                                                  |
| make dev_ui             | Run UI                                                                    |
| make -j2 dev_components | Run all components in parallell. Log output will be to the same terminal. |
| make dev_screen         | Run screen component                                                      |
| make dev_audio          | Run audio component                                                       |
