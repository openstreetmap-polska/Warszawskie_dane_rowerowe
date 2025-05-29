all: generate_diff osm_diff

osm_diff:
    uv run python osm_diff.py

generate_diff:
    uv run python generate_diff.py
