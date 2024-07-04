# Media component

## Installing

This project is built with Electron.

Run `npm install` from the media folder to install all dependencies.

## Running

Run the project with `node_modules/electron/dist/electron.exe .` from the media folder (use backslashes if running in Windows CMD).

### Available environment variables

| Name of variable                     | Function                                                                                                                       | Default value             |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | ------------------------- |
| SCREENCRASH_COMPONENT_ID             | Set name of component to be displayed in UI and logs                                                                           | Random string of 16 chars |
| SCREENCRASH_CORE                     | Set address to core                                                                                                            | localhost:8001            |
| SCREENCRASH_SUPPORTED_TYPES          | Space separated string of what types should be active. Available are: audio, video, image, web                                 | All available types       |
| SCREENCRASH_NO_WINDOW                | Set to `true` to disable visual components and hide display window. Affects SUPPORTED_TYPES if it has not been explicitly set. | false                     |
| SCREENCRASH_NO_AUDIO                 | Set to `true` to disable audio components. Affects SUPPORTED_TYPES if it has not been explicitly set.                          | false                     |
| SCREENCRASH_DISABLE_AUDIO_WORKAROUND | Set to `true` to disable playing a silent sound on loop, which is a workaround needed on some computers.                       | false                     |
| SCREENCRASH_FULLSCREEN               | Set to `true` to enable fullscreen mode. This cannot be used together with `SCREENCRASH_NO_WINDOW`.                            | false                     |
| SCREENCRASH_DISCONNECT_INFO          | Set to `false` to hide DISCONNECTED screen no matter if device is connected or not (good for live mode)                        | true                      |
| SCREENCRASH_WINDOW_BACKGROUND        | Set background color for window, in hex format. Default black. This cannot be used together with `SCREENCRASH_NO_WINDOW`.      | #000000                   |

## Visual Studio Code configuration

There is a run configuration available for the media module. Just open the entire repo folder in Visual studio code and
it should automagically know how to run etc. Yay!

## Using dummy-core to trigger actions

To run dummy-core, cd to the dummy_core directory and issue the command `npm start`.
Once in the dummy_core prompt, here are some examples that will trigger actions in the media component

```
/* Play video */
{"command": "create", "entityId": 1337, "channel": 1, "type": "video", "asset": "file:///C:/Users/matzl/Pictures/test_video.mp4"}
{"command": "show", "entityId": 1337, "channel": 1}
{"command": "play", "entityId": 1337, "channel": 1}

/* Show image */
{"command": "create", "entityId": 1338, "type": "image", "channel": 1, "asset": "file:///C:/Users/matzl/Pictures/options.PNG"}
{"command": "show", "entityId": 1338, "channel": 1}

/* Set viewport size (any media). All size arguments are optional. Defaults to top left corner, 100% width and height */
{"command": "viewport", "entityId": 1338, "x": 50, "y": 50, "width": 50, "height": 50, "usePercentage": false}
{"command": "viewport", "entityId": 1338, "width": 50, "usePercentage": true}

/* Setting viewport size with a mix of pixels and percentage */
{"command": "viewport", "entityId": 1338, "x": 0, "y": 0, "usePercentage": false}
{"command": "viewport", "entityId": 1338, "width": 50, "height": 50, "usePercentage": true}

/* Set layer (higher numbers are put on top of lower layers) */
{"command": "layer", "entityId": 1338, "layer": 10}

/* Advanced creation of media objects (combine commands) */
{"command": "create", "entityId": 1338, "type": "image", "channel": 1, "asset": "file:///C:/Users/matzl/Pictures/options.PNG", "x": 50, "y": 50, "width": 50, "height": 50, "usePercentage": false, "layer": 50}

{"command": "create", "entityId": 1338, "type": "image", "channel": 1, "asset": "file:///C:/Users/matzl/Pictures/options.PNG", "width": 50, "height": 50, "usePercentage": true, "visible": true, "layer": 10}
{"command": "create", "entityId": 1339, "type": "image", "channel": 1, "asset": "file:///C:/Users/matzl/Pictures/options.PNG", "visible": true, "layer": 5}
```

Change the asset paths to paths that exist on your file system. At the moment only MP4 files are supported for videos.
