# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
GENERATEDDIR  = $(SOURCEDIR)/generated
BUILDDIR      = _build
PROJECT_ROOT  = ..

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@echo Running '$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)'
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean: Makefile
	@echo Running '$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)'
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	rm -rf $(GENERATEDDIR)

# This recipe generates source files, so put result in source
# Seems to overwrite autosummary documentation though! So not using this rn
MODULE_EXCLUDE="../imas/examples/**" "../imas/**"
apidocs: Makefile
	sphinx-apidoc --implicit-namespaces -o "$(GENERATEDDIR)" "$(PROJECT_ROOT)/imaspy/" $(MODULE_EXCLUDE)

# Sphinx will run this automatically
autogen: Makefile
	sphinx-autogen -o "$(GENERATEDDIR)" $(SOURCEDIR)/*.rst

realclean: Makefile clean
	rm -rf $(SOURCEDIR)/apidoc $(GENERATEDDIR) $(SOURCEDIR)/_build/
