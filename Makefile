.PHONY: run docker-build docker-run

run:
	. venv/bin/activate && \
	./generate_diff.py && \
	./osm_diff.py

docker-build:
	docker build -t warszawskie_dane_rowerowe .

docker-run:
	docker run -it\
		-v $$(pwd)/.git:/app/.git \
		-v $$(pwd)/rowery_wawa:/app/rowery_wawa:ro \
		-v $$(pwd)/osm_diffs:/app/osm_diffs \
		-v $$(pwd)/latestDiff.geojson:/app/latestDiff.geojson \
		-t warszawskie_dane_rowerowe
