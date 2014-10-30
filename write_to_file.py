import settings
import json

#write_index = settings.ES_INDEX
write_index = "http://localhost:9200/doaj/"

def write_to_index(data_in, es_index):
    """
    Read from a file of ArticleBibJSON to populate an elasticsearch index with Articles.
    :param file_path: Path to file containing json dump
    :param es_index: Target index to write to.
    :return:
    """
    if type(data_in) == list:
        bibjson_list = data_in
    else:
        with open(data_in, 'rb') as f:
            bibjson_list = json.load(f, encoding='utf-8')

    for entry in bibjson_list:
        # Create a new Article for this bibjson
        print entry

