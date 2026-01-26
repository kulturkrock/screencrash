
* Båda datorerna

Stäng av notifikationer!
Stäng av wifi!

Anslut till styrdator till router via ethernet
Anslut projektor-dator till router (med långa sladden)

Kontrollera styrdatorns IP-adress (Inställningar -> Nätverk -> USB LAN)
t.ex. 192.168.1.136


* Projektordatorn (t.ex. Windows):

Starta Command Prompt (sök "terminal")

```
cd screencrash\screencrash\components\media
set SCREENCRASH_CORE=192.168.1.136:8001
npm run dev
```

F11 för full-screen

* Styrdatorn (t.ex. Mac)

SCREENCRASH_SYNC_ASSETS=true make dev_core
make dev_ui
SCREENCRASH_NO_WINDOW=true make dev_media


----------------------------------------------------------------------------------------------------------
-- Howto for conversion and other things

Convert to webm v9:

ffmpeg -i "test/2 transition.mp4" -c:v libvpx-vp9 -c:a libopus "test/2 transition.webm"


Convert to animated png:

ffmpeg -i "test/2 transition.mp4" -f apng "test/2 transition.png"


Negate colors:

ffmpeg -i input.mov -vf negate output.mov


Hue

ffmpeg -i input.mp4 -vf "hue=h=45:s=10" output.mp4


Concatenate

ffmpeg -i clip-1.MOV -q 0 clip-1.MTS

printf "file '%s'\n" fil1.mp4 fil2.mp4 > _concat.txt
ffmpeg -f concat -safe 0 -i _concat.txt -c copy ut.mp4

# different source types
ffmpeg -i "file1.mp4" -i "file2.mov" -i "file3.mov" \
    -filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a] concat=n=3:v=1:a=1 [outv] [outa]" \
    -map "[outv]" -map "[outa]" "out.mp4"


Convert to WEBM with fade-in/out

video_length=$(\
    ffprobe \
        -loglevel error \
        -select_streams v:0 \
        -show_entries stream=duration \
        -of default=noprint_wrappers=1:nokey=1 \
        "${file}" \
)

time_start="$(echo "${video_length}" - "${fade_out}" | bc)"
video_filter="fade=in:st=0:d=${fade_in}:alpha=1,fade=out:st=${time_start}:d=${fade_out}:alpha=1,format=yuva420p"

ffmpeg -i "${file}" -filter_complex "${video_filter}" -c:v libvpx-vp9 -c:a libopus -auto-alt-ref 0 "${out_file}"


* Examples of VAMP:ing

"42":
    prompt: "[starta introt]"
    next: "43"
    actions:
      - target: "video"
        cmd: "create"
        assets:
          - path: "film1.webm"
        params:
          entityId: "A"
          visible: true
          looping: 0
          seamless: true
          mimeCodec: 'video/webm; codecs="vp9, opus"'
      - target: "video"
        cmd: "set_next_file"
        assets:
          - path: "film2.webm"
        params:
          entityId: "A"
"43": ...
...
"567":
    prompt: "[döda film2]"
    next: "568"
    actions:
      - target: "video"
        cmd: "destroy"
        params:
          entityId: "A"




"699":
    prompt: "[Ganon, Diin, kungen, rådgivaren är på plats]"
    next: "701a"
    actions:
      - target: "video"
        cmd: "create"
        assets:
          - path: "Till föreställningen/0699 Krigsmontage2_part1.webm"
        params:
          entityId: "krig2"
          visible: true
          looping: 0
          seamless: true
          mimeCodec: 'video/webm; codecs="vp9, opus"'
      - target: "video"
        cmd: "set_next_file"
        assets:
          - path: "Till föreställningen/0699 Krigsmontage2_part2.webm"
        params:
          entityId: "krig2"
  "701a":
    prompt: "Det är dags att kriget får ett slut"
    next: "701b"
    actions:
      - target: "video"
        cmd: "set_next_file"
        assets:
          - path: "Till föreställningen/0699 Krigsmontage2_part3.webm"
        params:
          entityId: "krig2"
  "701b":
    prompt: "[Vampen slut, nästan direkt]"
    next: "710"
    actions:
      - target: "video"
        cmd: "set_next_file"
        assets:
          - path: "Till föreställningen/0699 Krigsmontage2_part4.webm"
        params:
          entityId: "krig2"
  "710":
    prompt: "Men hon är som besatt av sina magiska artefakter."
    next: "733a"
    actions:
      - target: "video"
        cmd: "set_next_file"
        assets:
          - path: "Till föreställningen/0699 Krigsmontage2_part5.webm"
        params:
          entityId: "krig2"
      - target: "video"
        cmd: "set_loops"
        params:
          entityId: "krig2"
          looping: 1
