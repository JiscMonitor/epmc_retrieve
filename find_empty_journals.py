# Find which journals are missing articles

import settings, requests, json

def find_empty_journals():

    SEARCH = settings.ES_INDEX + "/_search?pretty"
    RES_SIZE = 1000

    query = \
    {
        'fields' : ['index.issn'],
        'query' : { 'match_all' : {} },
        'size' : RES_SIZE
    }

    res_from = 0
    keep_looping = True
    j_issns = []
    a_issns = []

    while keep_looping:
        query['from'] = res_from
        resp = requests.get(SEARCH, data=json.dumps(query))
        results = resp.json()['hits']['hits']

        if results:
            for result in results:
                if result['_type'] == 'article':
                    a_issns += (result['fields']['index.issn'])
                elif result['_type'] == 'journal':
                    j_issns += (result['fields']['index.issn'])
        else:
            keep_looping = False
        res_from += RES_SIZE

    journal_issns = set(j_issns)
    article_issns = set(a_issns)

    print "Full list of journal ISSNs: {0}\t Set: {1}".format(len(j_issns),len(journal_issns))
    print "Full list of article ISSNs: {0}\t Set: {1}".format(len(a_issns),len(article_issns))

    diff = journal_issns.difference(article_issns)
    # print "\nJournals without articles:\n{0}".format(diff)

    return list(diff)
