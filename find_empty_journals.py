# Find which journals are missing articles

import settings, requests

search = settings.ES_INDEX + "journal/_search?pretty"

query = '{ query : { match_all : { } } }'

resp = requests.get(search, data=query)

print resp.text