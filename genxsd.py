import os
import sys
import argparse
import requests

parser = argparse.ArgumentParser(prog='genxsd.py')
parser.add_argument('-d', help='NDA datadictionary shortname', required=True)
nda_datatype = parser.parse_args().d

NDAR_URI = "https://ndar.nih.gov/api/datadictionary/v2/datastructure"

uri = "{0}/{1}".format(NDAR_URI, nda_datatype)
print "Requesting {} ...".format(uri)
r = requests.get(uri)

short_name = r.json()['shortName']
elem_name = short_name.upper()

XSD_HEAD = \
    '<?xml version="1.0" encoding="UTF-8"?>\n' \
    '<xs:schema targetNamespace="http://nrg.wustl.edu/nda"\n' \
    '    xmlns:nda="http://nrg.wustl.edu/nda"\n' \
    '    xmlns:xnat="http://nrg.wustl.edu/xnat"\n' \
    '    xmlns:xdat="http://nrg.wustl.edu/xdat"\n' \
    '    xmlns:xs="http://www.w3.org/2001/XMLSchema"\n' \
    '    elementFormDefault="qualified" ' \
    'attributeFormDefault="unqualified">\n' \
    '<xs:import namespace="http://nrg.wustl.edu/xnat" ' \
    'schemaLocation="../xnat/xnat.xsd"/>\n\n' \
    '<xs:element name="{0}" type="nda:{1}"/>\n\n' \
    '    <xs:complexType name="{2}">\n' \
    '        <xs:complexContent>\n' \
    '            <xs:extension base="xnat:subjectAssessorData">\n' \
    .format(elem_name, r.json()['shortName'], r.json()['shortName'])

XSD_ELEMENT = \
    '                <xs:element name="{0}" type="xs:{1}" ' \
    'minOccurs="0" maxOccurs="1">\n' \
    '                    <xs:annotation>\n' \
    '                        <xs:documentation>\n' \
    '                            {2}\n' \
    '                        </xs:documentation>\n' \
    '                    </xs:annotation>\n' \
    '                </xs:element>\n'

XSD_FOOT = \
    '            </xs:extension>\n' \
    '        </xs:complexContent>\n' \
    '    </xs:complexType>\n' \
    '</xs:schema>'


def buildXsd():
    print "Building XSD string"
    body = ''
    excluded = ['guid']

    for elem in r.json()['dataElements']:
        if elem['type'].lower() in excluded:
            continue

        body += XSD_ELEMENT.format(
            elem['name'], elem['type'].lower(), elem['description'])

    XSD_DOC = XSD_HEAD + body + XSD_FOOT

    return XSD_DOC


def writeXsd(xsd_str):
    if not os.path.exits('output'):
        os.makedirs('output')

    fname = 'output/' + nda_datatype + '.xsd'
    print "Writing XSD to {}".format(fname)

    with open(fname, 'w') as fout:
        fout.write(xsd_str)


if __name__ == "__main__":
    xsd_str = buildXsd()
    writeXsd(xsd_str)
