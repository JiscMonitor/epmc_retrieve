# Get missing article data from EPMC

import requests

ISSN_SEARCH = 'http://www.ebi.ac.uk/europepmc/webservices/rest/search/query=issn:'

resp = requests.get(ISSN_SEARCH + '0974-5181')
print resp.text
