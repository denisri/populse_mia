# Long version:
* [Sphinx Overview](http://www.sphinx-doc.org/en/master/index.html) and [Documenting Your Project Using Sphinx](https://pythonhosted.org/an_example_pypi_project/sphinx.html)
# Short version:

Note: Change below, `populse_mia` by the repository name.

## To install sphinx
          pip3 install sphinx

## In populse_mia's root folder
          mkdir docs/
          cd docs/

## To begin
          sphinx-quickstart
          
Then answer each question with default values, except the following ones:
 - Separate source and build directories (y/n) [n]: y
 - Project name: populse_mia
 - Author name(s): populse
 - Project version: 1
 - Project release: 1.0.0
 - autodoc: automatically insert docstrings from modules (y/n) [n]: y
 - Create Windows command file? (y/n) [y]: n  
 
The following lines (15-17) must be uncommented from docs/source/conf.py:
 - import os
 - import sys
 - sys.path.insert(0, os.path.abspath('../../python'))
 
The following line (8) must be modified from docs/Makefile:
 - `BUILDDIR      = BUILD`  become  `BUILDDIR      = .`  


## To update the api documentation (in docs/ folder)
          sphinx-apidoc -f -M -o source/ ../python/populse_mia/

## To generate the html pages (in docs/ folder)
          make html
