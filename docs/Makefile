SPHINXBUILD ?= uv run sphinx-build
SOURCEDIR = source
BUILDDIR = _build
SPHINXOPTS ?= -E -a -W -n -T

.PHONY: html clean

html:
	$(SPHINXBUILD) $(SPHINXOPTS) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html"

clean:
	rm -rf "$(BUILDDIR)"
