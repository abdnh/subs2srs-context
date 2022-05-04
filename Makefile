.PHONY: all zip clean fix mypy pylint install
all: zip

PACKAGE_NAME := subs2srs_context

zip: $(PACKAGE_NAME).ankiaddon

$(PACKAGE_NAME).ankiaddon: src/*
	rm -f $@
	rm -rf src/__pycache__
	( cd src/; zip -r ../$@ * )

# Install in test profile
install: src/*
	rm -rf src/__pycache__
	rm -rf ankiprofile/addons21/$(PACKAGE_NAME)
	cp -r src/. ankiprofile/addons21/$(PACKAGE_NAME)

fix:
	python -m black src
	python -m isort src

mypy:
	python -m mypy src

pylint:
	python -m pylint src

clean:
	rm -f $(PACKAGE_NAME).ankiaddon
