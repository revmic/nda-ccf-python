import sys
import os
import argparse
from hcpxnat.interface import HcpInterface

"""
Takes a CSV submitted to NDA by CCF contributor and uploads
"""

# hcpxnat module config
config_file = os.path.join(os.path.expanduser('~'), '.xnat_dev.cfg')
idb = HcpInterface(config=config_file)

# argument parser
parser = argparse.ArgumentParser(prog='genxsd.py')
parser.add_argument('-p', dest='project', required=True,
                    help='Project to upload to')
parser.add_argument('-f', dest='filename', required=True,
                    help='CSV filename to upload')
parser.add_argument('--create-subject', dest='create_subject', required=False,
                    action='store_true', help='Create the subject')
args = parser.parse_args()

idb.project = args.project
if not idb.projectExists():
    print "++ Project {} does not exists. Exiting...".format(args.project)
    sys.exit(1)


def createSubject():
    print "-- Creating subject {sub}".format(sub=idb.subject_label)

    if idb.subjectExists():
        print "++ {sub} already exists. Skipping creation.".format(
            sub=idb.subject_label)

    uri = '/REST/projects/{proj}/subjects/{sub}'.format(
        sub=idb.subject_label, proj=idb.project)
    idb.put(uri)


def readCsv():
    with open(args.filename, 'rU') as fp:
        lines = fp.read().split('\n')

    data = {}
    data['datatype'] = lines[0].split(',')[0]
    data['version'] = lines[0].split(',')[1]

    attributes = lines[1].split(',')
    rows = [l for l in lines[2:] if l]  # thow out blank lines
    records = [r.split(',') for r in rows]

    rows = len(records)
    cols = len(attributes)
    data_items = []

    for r in range(rows):
        row_data = {}
        for c in range(cols):
            row_data[attributes[c]] = records[r][c]
        data_items.append(row_data)

    data['items'] = data_items

    return data


def updateDatatype(data):
    pass


def populateDatatype(data):
    exp_label = data['datatype']
    idb.experiment_label = exp_label

    print "\n==============================="
    print "Uploading file {}\nHost: {}\nNDA datatype: {}\nProject: {}" \
        .format(args.filename, idb.url, data['datatype'], idb.project)
    print "===============================\n"

    for record in data['items']:
        idb.subject_label = record['subjectkey']

        if not idb.subjectExists():
            print "++ {sub} doesn't exist in project {proj}." \
                    .format(sub=idb.subject_label, proj=idb.project)

            if not args.create_subject:
                print "-- Use the --create-subject option or create in the UI."
                continue
            else:
                createSubject()

        # Create the experiment
        # uri = "/REST/projects/{p}/subjects/{s}/experiments/{e}?xsiType={x}" \

        uri = "/REST/projects/{p}/subjects/{s}/experiments/{e}?xsiType={x}" \
            .format(p=idb.project, s=idb.subject_label,
                    e=exp_label, x="nda:adi_200304")
        print uri
        idb.put(uri)

        for elem, val in record.iteritems():
            print elem, "--", val
            idb.setExperimentElement("nda:adi_200304", elem, val)


if __name__ == "__main__":
    data = readCsv()
    populateDatatype(data)
    sys.exit(0)
