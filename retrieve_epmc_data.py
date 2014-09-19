# Get missing article data from EPMC

import requests, time, json
from find_empty_journals import find_empty_journals
from models import ArticleBibJSON

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

        try:
            resp = requests.get(ISSN_SEARCH + j + params.format(page_index))
            resp_json = resp.json()
        except ValueError:
            print "Failed to get json for {0}".format(j)
            global failed
            failed.append(j)
            continue

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
        # Record ids to count them later
        global ids
        ids.append(res['id'])

        # Save a doaj-type bibjson object using the result
        a_bibjson = ArticleBibJSON()

        if 'title' in res:
            a_bibjson.title = res['title']

        if 'doi' in res:
            a_bibjson.add_identifier('doi', res['doi'])

        if 'journalInfo' in res:
            if 'issn' in res['journalInfo']:
                a_bibjson.add_identifier('pissn', res["journalInfo"]['journal']['issn'])

            if 'essn' in res['journalInfo']:
                a_bibjson.add_identifier('eissn', res["journalInfo"]['journal']['essn'])

            if 'volume' in res['journalInfo']:
                a_bibjson.volume = res['journalInfo']['volume']

            if 'issue' in res['journalInfo']:
                a_bibjson.number = res['journalInfo']['issue']

            if 'title' in res['journalInfo']:
                a_bibjson.journal_title = res['journalInfo']['journal']['title']

            if 'yearOfPublication' in res['journalInfo']:
                a_bibjson.year = res['journalInfo']['yearOfPublication']

            if 'monthOfPublication' in res['journalInfo']:
                a_bibjson.month = res['journalInfo']['monthOfPublication']

        if 'language' in res:
            a_bibjson.journal_language = res['language']

        if 'pageInfo' in res:
            try:
                [a_bibjson.start_page, a_bibjson.end_page] = res['pageInfo'].split('-')
            except ValueError:
                pass

        if 'fullTextUrlList' in res:
            for url_entry in res['fullTextUrlList']['fullTextUrl']:
                a_bibjson.add_url(url_entry['url'], 'fulltext', url_entry['documentStyle'])

        if 'abstractText' in res:
            a_bibjson.abstract = res['abstractText']

        if 'authorList' in res:
            for auth_entry in res['authorList']['author']:
                try:
                    name = u'{0} {1}'.format(auth_entry['firstName'], auth_entry['lastName'])
                except KeyError:
                    if 'fullName' in auth_entry:
                        name = auth_entry['fullName']
                    else:
                        name = auth_entry['collectiveName']
                if 'affiliation' in auth_entry:
                    affil = auth_entry['affiliation']
                else:
                    affil = None
                a_bibjson.add_author(name, None, affil)

        save(a_bibjson.bibjson)

def save(json_to_write):
    json.dump(json_to_write, save_file)
    save_file.write('\n')

if __name__ == '__main__':
    ids = []
    failed = []

    print "Checking the index for articles without journals...\n"
    empty_journals = find_empty_journals()

    save_file = open('article_json_sample', 'w')

    print "\nQuerying Europe PubMed Central...\n"
    check_epmc(empty_journals)

    print 'ids collected:\t {0}'.format(len(ids))
    print 'non-duplicates:\t {0}'.format(len(set(ids)))
    print 'failed issns:\t {0}'.format(len(failed))

    save_file.close()

