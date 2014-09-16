# Find which journals are missing articles

import settings, requests, json

def find_empty_journals():

    J_SEARCH = settings.ES_INDEX + "/journal/_search"

    j_query = \
    {
    "query" : {
        "bool" : {
            "must" : [
                { "term" : {"_type" : "journal"} },
                {"match" : {"index.country" : "United Kingdom"} }
                ]
        }
    },
    "facets" : {
        "issns" : {
            "terms" : {
                "field" : "index.issn.exact"
                }
            }
        }
    }

    RES_SIZE = get_count(J_SEARCH, j_query)
    j_query['facets']['issns']['terms']['size'] = RES_SIZE
    (j_issns, total_j_issns) = query_for_issns(J_SEARCH, j_query)

    print "Number of journal ISSNs: {0}\t Unique: {1}".format(total_j_issns, len(j_issns))

    A_SEARCH = settings.ES_INDEX + "/article/_search"

    a_query = \
    {
    "query" : {
        "bool" : {
            "must" : [
                { "term" : {"_type" : "article"} },
                {"match" : {"index.country" : "United Kingdom"} }
                ]
        }
    },
    "facets" : {
        "issns" : {
            "terms" : {
                "field" : "index.issn.exact"
                }
            }
        }
    }

    RES_SIZE = get_count(A_SEARCH, a_query)
    a_query['facets']['issns']['terms']['size'] = RES_SIZE
    (a_issns, total_a_issns) = query_for_issns(A_SEARCH, a_query)

    print "Number of article ISSNs: {0}\t Unique: {1}".format(total_a_issns, len(a_issns))

    diff = j_issns.difference(a_issns)
    print "Journals without articles: {0}".format(len(diff))

    return list(diff)

def query_for_issns(url, query):
    result_set = set()

    resp = requests.get(url, data=json.dumps(query))
    results = resp.json()['facets']['issns']

    total_issns = results['total']

    if total_issns > 0:
        for result in results['terms']:
            result_set.add(result['term'])

    return (result_set, total_issns)


def get_count(url, query):
    resp = requests.get(url, data=json.dumps(query))
    return resp.json()['facets']['issns']['total']

if __name__ == '__main__':
    find_empty_journals()
