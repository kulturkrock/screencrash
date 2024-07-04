# Myggcheck

## Purpose
Sometimes the wireless microphones (myggor) stop working. It would be nice to be able to communicate this backstage without having to move from the mixing stage. This allows you to do it by sending a message to a status screen. It's all it does.

## Building
It should be sufficient to run `make dev` to build and start it. The component is very similar to media.

## Variables to control it
Use the environment variable `SCREENCRASH_CORE` to enlighten this component on where to find the core component.

Use the environment variable `SCREENCRASH_COMPONENT_ID` to give this component instance a name.