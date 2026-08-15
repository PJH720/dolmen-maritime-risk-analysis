.PHONY: setup data ocean parse grid model figures all clean
setup:
	conda env create -f environment.yml
data:
	python src/acquire/khs_korea.py
	python src/acquire/osm_megaliths.py
	python src/acquire/basemap.py
ocean:
	python src/acquire/ocean.py
	python src/acquire/era5_waves.py
parse:
	python src/features/parse_ysg.py
	python src/features/geocode_ri.py
grid:
	python src/features/build_grid.py
	python src/features/marine_exposure.py
model:
	python src/models/analysis.py
	python src/models/spatial.py
figures:
	python src/viz/figures.py
diag:
	python src/features/survey_bias.py
all: data ocean parse grid model figures
clean:
	rm -rf data/raw/* data/interim/* && touch data/raw/.gitkeep data/interim/.gitkeep
