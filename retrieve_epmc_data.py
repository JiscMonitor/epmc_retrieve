# Get missing article data from EPMC

import requests, time
from lxml import etree
from find_empty_journals import find_empty_journals

ISSN_SEARCH = 'http://www.ebi.ac.uk/europepmc/webservices/rest/search/query=issn:'
RESULT_TYPE = '&resulttype=core'

DELAY = 1   # Seconds delay between requests

empty_journals = find_empty_journals()

print "\nQuerying Europe PubMed Central...\n"

parser = etree.XMLParser(encoding='utf-8', recover=True, ns_clean=True)
found_count = 0
article_count_list = []

for j in empty_journals:
    resp = requests.get(ISSN_SEARCH + j + RESULT_TYPE)
    xml_tree = etree.fromstring(resp.text.encode('utf-8'), parser=parser)

    hits = int(xml_tree.find('hitCount').text)
    if hits > 0:
        found_count += 1
        article_count_list.append(found_count)
        #print etree.tostring(xml_tree)

    time.sleep(DELAY)

print "{0} Journals found in EPMC, covering a total of {1} articles, with a mean of {2} articles per journal.".format(found_count, sum(article_count_list), sum(article_count_list) / float(found_count))
