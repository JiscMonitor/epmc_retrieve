# Get missing article data from EPMC

import requests, time
from find_empty_journals import find_empty_journals

ISSN_SEARCH = 'http://www.ebi.ac.uk/europepmc/webservices/rest/search/query=issn:'

RESULT_TYPE = '&resulttype=core'
FORMAT = '&format=json'
PAGE = '&page={0}'
params = RESULT_TYPE + FORMAT + PAGE
DELAY = 1   # Seconds delay between requests to EPMC

empty_journals = find_empty_journals()

print "\nQuerying Europe PubMed Central...\n"
found_count = 0
article_count_list = []

for j in empty_journals[:20]:
    page_index = 1
    resp = requests.get(ISSN_SEARCH + j + params.format(page_index))
    resp_json = resp.json()

    hits = resp_json['hitCount']
    if hits > 0:
        found_count += 1
        article_count_list.append(hits)

    time.sleep(DELAY)

print "{0} Journals found in EPMC, covering a total of {1} articles, with a mean of {2} articles per journal.".format(found_count, sum(article_count_list), sum(article_count_list) / float(found_count))
