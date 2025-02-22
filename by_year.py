#!/bin/python
import json

from collections import defaultdict
from datetime import date, datetime
from io import BytesIO
from json import loads
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET
from zipfile import ZipFile


# NOTE: The API does not appear to contain the latest version anymore
#       so you may need to manually download the zip file and create
#       data.xml manually
with open('./URL') as f:
    URL = next(f)

EXTENSIONS = {
    file.stem: loads(file.read_text())
    for file in Path('.').glob('extensions/*.json')
}


def open_xml_file():
    file = Path('data.xml')
    if not file.exists():
        try:
            response = urlopen(URL)
        except Exception:
            exit('Please update the URL file!')

        zipfile = ZipFile(BytesIO(response.read()))
        xml = next(name for name in zipfile.namelist() if name.endswith('xml'))

        with file.open('wb') as f:
            f.write(zipfile.open(xml).read())

    return file.open()


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
    max_year = max(years)

    for district in districts:
        id = int(district.find('districtHistId').text)
        name = district.find('districtShortName').text

        start = as_date(district.find('districtAdmissionDate').text)
        end = district.find('districtAbolitionDate')
        end = as_date(end.text) if end is not None else date(max_year, 12, 31)

        for year in range(start.year, end.year + 1):
            by_year_and_id[(year, id)] = name

    return by_year_and_id


def as_date(text):
    return datetime.strptime(text, '%Y-%m-%d').date()


def extend(year, canton, data):
    extension = EXTENSIONS.get(canton)
    if extension and year >= extension['since']:
        for number in data:
            additional_data = extension.get(str(number), {})
            data[number].update(additional_data)
            if not additional_data:
                print(
                    '\nWarning: No extension data for {} {} {}'.format(
                        year, canton.upper(), number
                    )
                )

    return data


def build_years():
    root = ET.parse(open_xml_file())
    max_year = int(root.find('validFrom').text.split('-')[0])

    years = set(range(1960, max_year + 1))
    print(
        'Building {}-{}\n'.format(min(years), max(years)), end='', flush=True
    )

    by_year = {year: defaultdict(dict) for year in years}

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
        end = as_date(end.text) if end is not None else date(max_year, 12, 31)

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
        # '_all.json': lambda year, canton: by_year,
        # '{year}/_all.json': lambda year, canton: by_year[year],
        '{year}/{canton}.json': lambda year, canton: by_year[year][canton]
    }

    created = set()

    for year, cantons in by_year.items():
        print('.', end='', flush=True)

        for canton in cantons:
            for output, get in outputs.items():

                path = basepath / output.format(year=year, canton=canton)

                if path in created:
                    continue

                if not path.parent.exists():
                    path.parent.mkdir(parents=True)

                with path.open('w') as f:
                    data = get(year, canton)
                    data = extend(year, canton, data)
                    json.dump(data, f, indent=4, sort_keys=True)

                created.add(path)

    print('\nDone!\n')


if __name__ == '__main__':
    build_years()
