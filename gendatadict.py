import sys
import csv
import argparse
import requests
# import xml.etree.ElementTree as ET
reload(sys)
sys.setdefaultencoding('UTF8')

NDAR_URI = "https://ndar.nih.gov/api/datadictionary/v2/datastructure"

parser = argparse.ArgumentParser(prog='genxsd.py')
parser.add_argument('-d', help='NDA datadictionary shortname', required=True)
# parser.add_argument('-c', help='Data Dictionary Category Name', required=True)
# parser.add_argument('-a', help='Data Dictionary Assessment Name', required=True)
parser.add_argument('-p', help='Comma separated list of projects')
nda_datatype = parser.parse_args().d
project_list = parser.parse_args().p
# nda_datatype = 'adi_200304'

fname = 'output/' + nda_datatype + '-datadict.csv'
print "Writing CSV to", fname
csvWriter = csv.writer(open(fname, 'w'), quoting=csv.QUOTE_ALL)

uri = "{0}/{1}".format(NDAR_URI, nda_datatype)
print "Getting {} ...".format(uri)
r = requests.get(uri)

# print "Categories:", r.json()['categories']
category = r.json()['categories'][0]  # Currently grabbing first category
assessment = r.json()['dataType']


def createCsv():
    print "Creating CSV"
    count = 0

    # Write a row for each data element for the Connectome datadict CSV
    for elem in r.json()['dataElements']:
        attr = []
        excluded = ['guid']

        if elem['type'].lower() in excluded:
            continue

        # name
        attr.append(elem['name'].upper())
        # category
        attr.append(category)
        # assessment
        attr.append(assessment)
        # fullDisplayName
        attr.append(elem['description'])
        # dictType
        attr.append(elem['type'])
        # values
        attr.append(getValues(elem))
        # columnHeader
        attr.append(generateColumnHeader(elem))
        # validationMessage
        attr.append(getValidationMessage(elem))
        # validation
        attr.append(generateValidationRegex(elem))
        # operators
        attr.append(getOperators(elem))
        # watermark
        attr.append(getValidationMessage(elem))
        # xsiType
        attr.append('nda:{0}'.format(nda_datatype))
        # fieldId
        attr.append(elem['name'].upper())
        # description
        attr.append(getNotes(elem))
        # tier
        attr.append(0)
        # projects
        attr.append(generateProjectList())

        # attr.append(str(elem['position']))  # or maybe count

        csvWriter.writerow(attr)
        count += 1


def getValues(elem):
    if elem['type'] == 'Boolean':
        return '{ "true": "True", "false": "False" }'

    if elem['valueRange'] and elem['valueRange'].lower() == 'yes;no':
        return '{"Yes":"Yes","No":"No"}'

    values = ""
    # If there's a note that contains '=' and no value range
    # This should be the case for deterministic key value pairs without ranges
    if hasValueChoices(elem) and elem['notes']:
        # Split up the values and remove leading/trailing whitespace
        value_groups = elem['notes'].replace('\n', '').split(';')
        values += '{'

        for pair in value_groups:
            # print "PAIR", pair.strip()
            # TODO - Need to handle semi-colons within pairs
            try:
                key = pair.split('=')[0]
                val = pair.split('=')[1]
            except IndexError:
                print "Looks like there was a ';' in this key value pair."
                print "PAIR --", pair

            key_val = '"{}":"{}",'.format(key.strip(), val.strip())
            values += key_val

        # Remove trailing comma
        values = values[:-1]
        values += '}'

    return values


def generateValidationRegex(elem):
    validation = ''

    if hasValueChoices(elem):
        return validation

    if elem['type'] == 'Float':
        return '^[-+]?[0-9]*[.]?[0-9]+$'

    # If there's a value range and the first character is a digit
    # TODO - Does this find everywhere a regex is needed?
    if elem['valueRange'] and elem['valueRange'][0].isdigit():
        validation += '^('
        value_groups = elem['valueRange'].split(';')
        value_count = len(value_groups)
        cur_count = 0

        for group in value_groups:
            cur_count += 1

            # Indicates a range of numbers
            if '::' in group:
                start = int(group.split('::')[0])
                end = int(group.split('::')[1])

                for i in range(start, end+1):
                    validation += str(i) + '|'
            else:  # Indicates single number
                validation += str(group) + '|'

            # Get rid of trailing '|' if last element
            if cur_count == value_count:
                validation = validation[:-1]

        validation += ')$'

    return "".join(validation.split())


def getValidationMessage(elem):
    if hasValueChoices(elem):
        return

    validation_message = ""
    if elem['valueRange']:
        _range = elem['valueRange'].replace("::", "-")
        validation_message = "Must be {0} {1}".format(elem['type'], _range)
    return validation_message


def getNotes(elem):
    if elem['notes']:
        return elem['notes']
    else:
        return " "


def generateColumnHeader(elem):
    return elem['name'].title()


def generateProjectList():
    proj_list = ''
    proj_count = len(project_list.split(','))
    cur_count = 0

    if project_list:
        proj_list += '['
        for proj in project_list.split(','):
            proj_list += '"'
            proj_list += proj
            cur_count += 1

            if cur_count == proj_count:
                proj_list += '"'  # Last project in list
            else:
                proj_list += '",'  # Need comma otherwise
        proj_list += ']'

    return proj_list


def getOperators(elem):
    if elem['type'] == 'Boolean':
        return '{ "=": "="}'
    elif hasValueChoices(elem):
        # Doesn't totally make sense for strings/ints that are actually boolean
        return '{ "=": "=", "!=": "NOT =" }'
    elif elem['type'] == 'String' and not hasValueChoices(elem):
        return '{ "=": "=", "!=": "NOT =", "CONTAINS": "CONTAINS", ' + \
            '"!CONTAINS": "DOESN\'T CONTAIN","\'NULL\'": "IS EMPTY", ' + \
            '"\'NOT NULL\'": "IS NOT EMPTY" }'

    elif elem['type'] == 'Float' or elem['type'] == 'Integer':
        return '{ "=": "=", "!=": "NOT =", "<": "<", ">": ">" }'
    else:
        return "NONE"
        # return '{ "=": "=", "!=": "NOT =" }'


def hasValueChoices(elem):
    # Infer whether element has distinct choices
    # Some types, we know for certain (?)
    if elem['type'] == 'Boolean':
        return True
    elif elem['type'] == 'Float':
        return False
    elif elem['valueRange'] and 'yes' in elem['valueRange'].lower():
        return True
    elif (elem['notes'] and '=' in elem['notes']):  # and \
       # (elem['valueRange'] and '::' not in elem['valueRange']):
        return True
    else:
        return False


def hasBooleanChoice(elem):
    if elem['type'] == 'Boolean':
        return True
    else:
        return False


if __name__ == "__main__":
    # csv_str = createCsv()
    createCsv()
    # writeCsv(csv_str)
    print "DONE"
