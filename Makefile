ETAGS_FILES = \
	play.py \
	Bigrams.py \
	API.py \
	~/lib/python/noodle/*.py

all: TAGS

TAGS: $(ETAGS_FILES) Makefile
	etags $(ETAGS_FILES)

clean_tags:
	rm -f TAGS

clean: clean_tags
