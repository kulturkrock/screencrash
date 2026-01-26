
.PHONY: help convert opus

# Input files (feel free to change file names).
# Downloaded from Google:
CSV = "Skärmkrock-manus - Manus.csv"
# PDF script:
MANUS = "Vintergatan_20250310.pdf"

# File that Screencrash can read (don't change the file name):
OPUS = "real_opus.yaml"


help:
	@echo "make convert | convert-force | opus"

convert:
	python ../scripts/convert_videos.py -i $(CSV) -r google-media/ -d media/ -v

convert-force:
	python ../scripts/convert_videos.py -i $(CSV) -r google-media/ -d media/ -v --force

opus:
	python ../scripts/opus_from_csv.py -i $(CSV) -o $(OPUS) -s $(MANUS) -d media/

