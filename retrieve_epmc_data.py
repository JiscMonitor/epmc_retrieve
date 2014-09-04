# Get missing article data from EPMC

import requests, time
from lxml import etree
from find_empty_journals import find_empty_journals

ISSN_SEARCH = 'http://www.ebi.ac.uk/europepmc/webservices/rest/search/query=issn:'
RESULT_TYPE = '&resulttype=core'

DELAY = 1   # Seconds

empty_journals = find_empty_journals()
print "Number of empty journals {0}".format(len(empty_journals))

parser = etree.XMLParser(encoding='utf-8', recover=True, ns_clean=True)
found_count = 0

for j in empty_journals[:100]:
    resp = requests.get(ISSN_SEARCH + j + RESULT_TYPE)
    xml_tree = etree.fromstring(resp.text.encode('utf-8'), parser=parser)

    hits = int(xml_tree.find('hitCount').text)
    if hits > 0:
        found_count += 1
        print etree.tostring(xml_tree)

    '''
    for child in xml_tree.iterchildren():
        if child.tag == 'hitCount':
            if child.text == '0':
                pass
    '''
    time.sleep(DELAY)

print found_count
