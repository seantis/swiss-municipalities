#!/bin/python
import json

from collections import defaultdict
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET
from zipfile import ZipFile


with open('./URL') as f:
    URL = next(f)


def open_xml_file():
    zipfile = ZipFile(BytesIO(urlopen(URL).read()))
    xml = next(name for name in zipfile.namelist() if name.endswith('xml'))
    return zipfile.open(xml)


def filter_path(root, path, filters=None):
    filters = filters or tuple()

    for el in root.findall(path):

        for filter in filters:
            if not filter(el):
                break
        else:
            yield el


def districts_by_year_and_id(root, years):
    districts = filter_path(root, './districts/district', (
        # only actual districts
        lambda el: el.find('districtEntryMode').text == '15',
    ))

    by_year_and_id = {year: defaultdict(dict) for year in years}

    for district in districts:
        id = int(district.find('districtHistId').text)
        name = district.find('districtShortName').text

        start = as_date(district.find('districtAdmissionDate').text)
        end = district.find('districtAbolitionDate')
        end = as_date(end.text) if end is not None else date.today()

        for year in range(start.year, end.year + 1):
            by_year_and_id[(year, id)] = name

    return by_year_and_id


def as_date(text):
    return datetime.strptime(text, '%Y-%m-%d').date()


def build_years():
    years = set(range(1960, date.today().year + 1))
    print("Building {}-{}".format(min(years), max(years)), end='', flush=True)

    by_year = {year: defaultdict(dict) for year in years}

    root = ET.parse(open_xml_file())

    municipalities = filter_path(root, './municipalities/municipality', (
        # only finalized entries
        lambda el: el.find('municipalityStatus').text == '1',

        # only towns (not lakes or other)
        lambda el: el.find('municipalityEntryMode').text == '11'
    ))

    districts = districts_by_year_and_id(root, years)

    for municipality in municipalities:
        id = int(municipality.find('municipalityId').text)
        canton = municipality.find('cantonAbbreviation').text.lower()
        name = municipality.find('municipalityLongName').text
        district_id = int(municipality.find('districtHistId').text)

        start = as_date(municipality.find('municipalityAdmissionDate').text)
        end = municipality.find('municipalityAbolitionDate')
        end = as_date(end.text) if end is not None else date.today()

        for year in range(start.year, end.year + 1):
            # newer entries will replace older entries in a few instances:
            # * there's a geopgrahical change (no consequence for us)
            # * there's a new town/merger/secession in the middle of the year
            #   in which case we just take the latest record of the year
            #   (there are only a handful cases where this happened)
            # * there's a district change in the middle of the year, in which
            #   case we also just use the latest record of the year
            by_year[year][canton][id] = {'name': name}

            district = districts.get((year, district_id))
            if district:
                by_year[year][canton][id]['district'] = district

    basepath = Path.cwd() / 'by_year'
    outputs = {
        '_all.json': lambda year, canton: by_year,
        '{year}/_all.json': lambda year, canton: by_year[year],
        '{year}/{canton}.json': lambda year, canton: by_year[year][canton]
    }

    created = set()

    for year, cantons in by_year.items():
        print(".", end='', flush=True)

        for canton in cantons:
            for output, get in outputs.items():

                path = basepath / output.format(year=year, canton=canton)

                if path in created:
                    continue

                if not path.parent.exists():
                    path.parent.mkdir(parents=True)

                with path.open('w') as f:
                    json.dump(get(year, canton), f, indent=4, sort_keys=True)

                created.add(path)


if __name__ == '__main__':
    build_years()
