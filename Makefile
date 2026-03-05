.PHONY: all boundaries viirs dmsp stats geojson clean

PY=python
CFG=configs/config.yaml

all: boundaries viirs stats geojson

boundaries:
	$(PY) -m ntl_pipeline.cli download-boundaries --config $(CFG)

viirs:
	$(PY) -m ntl_pipeline.cli download-viirs --config $(CFG)
	$(PY) -m ntl_pipeline.cli prep-rasters --config $(CFG) --source viirs

# optional older series
# dmsp:
# 	$(PY) -m ntl_pipeline.cli download-dmsp --config $(CFG)
# 	$(PY) -m ntl_pipeline.cli prep-rasters --config $(CFG) --source dmsp

stats:
	$(PY) -m ntl_pipeline.cli zonal-stats --config $(CFG)

geojson:
	$(PY) -m ntl_pipeline.cli export-geojson --config $(CFG)

clean:
	rm -rf data/processed/* output/*
