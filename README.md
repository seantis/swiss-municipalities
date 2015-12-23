Swiss Municipalities as JSON
============================

This repository provides useful data around Swiss Municipalities from the
"Historisiertes Gemeindeverzeichnis" (historical municipalities directory)
provided by the Swiss government:

[http://www.bfs.admin.ch/bfs/portal/de/index/infothek/nomenklaturen/blank/blank/gem_liste/02.html](http://www.bfs.admin.ch/bfs/portal/de/index/infothek/nomenklaturen/blank/blank/gem_liste/02.html)

The provided data is very thorough but not easy to deal with. It's a pretty
information-dense XML file. This repository means to build useful JSON data
using said XML. Data that can be understood without reading a lengthy manual.

So far there's only one resulting output, but there may be more.

## Outputs

### Municipalities by Year/Canton/Id (BFS-Nummer)

The `by_year.py` python script provides the full municipality name as well as
the district - if available - keyed by the id/BFS-Nummer. It provides separate
files by year and canton as well as one large file with all years and all
cantons.

To generate the latest data run `python by_year.py`. Note that this script
requires Python 3.4+.

## URL

The `URL` file contains the url to the "Historisiertes Gemeindeverzeichnis
der Schweiz (XML Format)" zip file of the Swiss Governement. This url may
change over time (especially when new data is released around new year). It is
found on the website mentioned at the beginning of this readme.
