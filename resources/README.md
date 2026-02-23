
# Setting up Skärmkrock from Google drive

We assume that the relevant files are stored on Google drive:

- the musical script as a generated PDF (called, say `Musikal-manus.pdf`)
- the Skärmkrock script as a Google-sheet (called, say `Skärmkrock-manus`)
- all media files (in a directory that can be called `google-media`)

You need `ffmpeg` for converting videos.

**tl;dr**:
Run `make help` and follow the guidelines.


## Converting files

1. Download all files:
  - Download the PDF script (`Musikal-manus.pdf`)
  - Export the Skärmkrock script from Google sheets, as a CSV file (`Skärmkrock-manus.csv`).
  - Download all media files into the folder `google-media`.
  - Create the folder `media`.

2. Edit the variables `CSV`, `SCRIPT` and `UNCONVERTED-MEDIA` in the Makefile.

3. Run `make convert`. This copies/converts media files into the folder `media`.

4. Run `make opus`. This creates the Skärmkrock driver file `real_opus.yaml`.


## Testing Skärmkrock

Open 3 new terminal windows in the `screencrash` directory (parent to the directory, `resources`). Run the following in each window:

1. Start the server: `make -C core dev`. (If this doesn't work you can instead run `make -C core test`.)

2. Start the UI: `make -C ui dev`. This should open Google Chrome with the UI webpage.

3. Start the media server: `make -C components/media dev`. This opens the Electron app with a black window.

Put the Chrome window and the Electron window so you can see both.

Now you can move around in the UI and see how it will look like in the Electron window.


## Running Skärmkrock with projector, on two computers

Important:
- Turn off notifications!
- Turn off wifi!

Preparitions:
- Connect the controlling (UI) computer to the router via a short ethernet cable.
- Connect the projector computer to the router via the long ethernet cable.

Check the IP address of the controlling computer (let's say it is 192.168.1.136).

### On the projector computer

Assuming it is Windows, start the Command Prompt:

```
cd screencrash\screencrash\components\media
set SCREENCRASH_CORE=192.168.1.136:8001
npm run dev
```

Now Electron should start on the projector: Press F11 for full-screen.

### On the controlling computer

Assuming it is a Mac or Linux. Run on three different terminals:

1. `SCREENCRASH_SYNC_ASSETS=true make -C core dev`
2. `make -C ui dev`
3. `SCREENCRASH_NO_WINDOW=true make -C components/media dev`
