.PHONY: setup data diag clean
setup:
	conda env create -f environment.yml
data:
	python src/acquire/khs_korea.py
	python src/acquire/osm_megaliths.py
	python src/acquire/basemap.py
diag:
	python src/features/survey_bias.py
clean:
	rm -rf data/raw/* data/interim/* && touch data/raw/.gitkeep data/interim/.gitkeep
