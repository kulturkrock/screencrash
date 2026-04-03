
.PHONY: help convert opus

# Input files (feel free to change file names).
# Downloaded from Google drive:
CSV = "Skärmkrock-manus - Manus.csv"
# PDF script:
SCRIPT = "Musikal-manus.pdf"

# Unconverted media files (e.g., downloaded from Google drive)
UNCONVERTED_MEDIA = "google-media"
# Converted media files (all videos are in .webm format)
CONVERTED_MEDIA = "media"

# File that Screencrash can read (don't change the file name):
OPUS = "real_opus.yaml"


help:
	@echo "1. download the PDF script into '$(SCRIPT)' "
	@echo "2. download the Skärmkrock script into '$(CSV)' "
	@echo "3. download all media files into '$(UNCONVERTED_MEDIA)'"
	@echo "4. run 'make convert', which converts the media files into '$(CONVERTED_MEDIA)'"
	@echo "   (or 'make convert-force' to force conversion of all files)"
	@echo "5. run 'make opus', which creates the opus file '$(OPUS)'"

convert:
	python ../scripts/convert_videos.py -i $(CSV) -r $(UNCONVERTED_MEDIA) -d $(CONVERTED_MEDIA) -v

convert-force:
	python ../scripts/convert_videos.py -i $(CSV) -r $(UNCONVERTED_MEDIA) -d $(CONVERTED_MEDIA) -v --force

opus:
	python ../scripts/opus_from_csv.py -i $(CSV) -o $(OPUS) -s $(SCRIPT) -d $(CONVERTED_MEDIA)

