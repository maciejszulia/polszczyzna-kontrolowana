PY ?= python
# MEASURE_FLAGS=--offline reuses results/p3_tokens.json and results/p5_corpus.json (no network).
MEASURE_FLAGS ?=
PAPER = abstract body_1_model body_2_measure body_3_probe body_4_corpus body_5_philosophy body_6_conclusions

.PHONY: all test measure figures lint paper clean

all: test measure figures lint paper

test:
	$(PY) -m pytest -q

measure:
	$(PY) scripts/measure.py $(MEASURE_FLAGS)

figures: measure
	$(PY) scripts/figures.py

lint:
	$(PY) -m src.pklint --tex $(PAPER:%=paper/%.tex) paper/measurement_report_pl.tex paper/report_problems.tex paper/report_models.tex

paper:
	cd paper && pdflatex -interaction=nonstopmode pk_complexity_pl.tex >/dev/null
	cd paper && pdflatex -interaction=nonstopmode pk_complexity_pl.tex >/dev/null
	cd paper && pdflatex -interaction=nonstopmode measurement_report_pl.tex >/dev/null
	cd paper && pdflatex -interaction=nonstopmode measurement_report_pl.tex >/dev/null
	@echo "paper/pk_complexity_pl.pdf paper/measurement_report_pl.pdf"

clean:
	rm -f paper/*.aux paper/*.log paper/*.out paper/*.toc
	rm -rf __pycache__ src/__pycache__ tests/__pycache__ scripts/__pycache__ .pytest_cache
