# Get missing article data from EPMC

import requests, time
from find_empty_journals import find_empty_journals

ISSN_SEARCH = 'http://www.ebi.ac.uk/europepmc/webservices/rest/search/query=issn:'

RESULT_TYPE = '&resulttype=core'
FORMAT = '&format=json'
PAGE = '&page={0}'
params = RESULT_TYPE + FORMAT + PAGE
DELAY = 1   # Seconds delay between requests to EPMC

def check_epmc(journal_list):
    found_count = 0
    article_count_list = []

    for j in journal_list:
        page_index = 1

        resp = requests.get(ISSN_SEARCH + j + params.format(page_index))
        resp_json = resp.json()

        # Check if we have anything to work with
        hits = resp_json['hitCount']
        if hits > 0:
            found_count += 1
            article_count_list.append(hits)

            # get the first set of results
            results = resp_json['resultList']['result']

            while results:
                handle_results(results)

                # Get a new set of results, paging 25 at a time
                page_index += 1
                resp = requests.get(ISSN_SEARCH + j + params.format(page_index))
                resp_json = resp.json()
                results = resp_json['resultList']['result']
                time.sleep(DELAY)

        time.sleep(DELAY)

    print "{0} Journals found in EPMC, covering a total of {1} articles, with a mean of {2} articles per journal.".format(found_count, sum(article_count_list), sum(article_count_list) / float(found_count))

def handle_results(result_batch):
    for res in result_batch:
        global ids
        ids.append(res['id'])
        # Save a doaj-type bibjson object using the result
        #a_bibjson = {}
        #a_bibjson['title'] = res['title']
        #save(a_bibjson)
        #save(res)

def save(json):
    print json

if __name__ == '__main__':
    ids = []

    print "Checking the index for articles without journals...\n"
    empty_journals = find_empty_journals()

    print "\nQuerying Europe PubMed Central...\n"
    check_epmc(empty_journals)

    print 'ids collected:\t {0}'.format(len(ids))
    print 'minus duplicates:\t {0}'.format(len(set(ids)))

