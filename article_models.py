import json, requests, uuid
from copy import deepcopy
from datetime import datetime
import time

import settings
from bibjson_models import ArticleBibJSON

# debugging
import traceback, sys

class DomainObject(object):
    __type__ = None # set the type on the model that inherits this

    def __init__(self, **kwargs):
        if '_source' in kwargs:
            self.data = dict(kwargs['_source'])
            self.meta = dict(kwargs)
            del self.meta['_source']
        else:
            self.data = dict(kwargs)

    @classmethod
    def target_whole_index(cls):
        t = settings.ES_INDEX
        return t

    @classmethod
    def target(cls):
        t = cls.target_whole_index()
        t += cls.__type__ + '/'
        return t

    @classmethod
    def makeid(cls):
        '''Create a new id for data object
        overwrite this in specific model types if required'''
        return uuid.uuid4().hex

    @property
    def id(self):
        return self.data.get('id', None)

    def set_id(self, id=None):
        if id is None:
            id = self.makeid()
        self.data["id"] = id

    @property
    def version(self):
        return self.meta.get('_version', None)

    @property
    def json(self):
        return json.dumps(self.data)

    def set_created(self, date=None):
        if date is None:
            self.data['created_date'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            self.data['created_date'] = date

    @property
    def created_date(self):
        return self.data.get("created_date")

    @property
    def last_updated(self):
        return self.data.get("last_updated")

    def save(self, retries=0, back_off_factor=1):
        if 'id' in self.data:
            id_ = self.data['id'].strip()
        else:
            id_ = self.makeid()
            self.data['id'] = id_

        self.data['last_updated'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        if 'created_date' not in self.data:
            self.data['created_date'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        attempt = 0
        url = self.target() + self.data['id']
        d = json.dumps(self.data)
        while attempt <= retries:
            try:
                r = requests.post(url, data=d)
                if r.status_code >= 400 and r.status_code < 500:
                    # bad request, no retry
                    print "bad request", r.json()
                    traceback.print_stack(file=sys.stdout)
                    break
                elif r.status_code >= 500:
                    print "server error", r.json()
                    attempt += 1
                else:
                    return r

            except requests.ConnectionError:
                attempt += 1

            # wait before retrying
            time.sleep((2**attempt) * back_off_factor)

    @classmethod
    def bulk(cls, bibjson_list, idkey='id', refresh=False):
        data = ''
        for r in bibjson_list:
            data += json.dumps( {'index':{'_id':r[idkey]}} ) + '\n'
            data += json.dumps( r ) + '\n'
        r = requests.post(cls.target() + '_bulk', data=data)
        if refresh:
            cls.refresh()
        return r.json()


    @classmethod
    def refresh(cls):
        r = requests.post(cls.target() + '_refresh')
        return r.json()


    @classmethod
    def pull(cls, id_):
        '''Retrieve object by id.'''
        if id_ is None:
            return None
        try:
            out = requests.get(cls.target() + id_)
            if out.status_code == 404:
                return None
            else:
                return cls(**out.json())
        except:
            return None

    def delete(self):
        r = requests.delete(self.target() + self.id)

    @classmethod
    def remove_by_id(cls, id):
        r = requests.delete(cls.target() + id)

    @classmethod
    def delete_by_query(cls, query):
        r = requests.delete(cls.target() + "_query", data=json.dumps(query.get("query")))
        return r

    @classmethod
    def destroy_index(cls):
        r = requests.delete(cls.target_whole_index())
        return r

    def update(self, doc):
        """
        add the provided doc to the existing object
        """
        return requests.post(self.target() + self.id + "/_update", data=json.dumps({"doc" : doc}))

    @classmethod
    def delete_all(cls):
        r = requests.delete(cls.target())
        r = requests.put(cls.target() + '_mapping', json.dumps(app.config['MAPPINGS'][cls.__type__]))

    @classmethod
    def iterate(cls, q, page_size=1000, limit=None, wrap=True):
        q["size"] = page_size
        q["from"] = 0
        if "sort" not in q: # to ensure complete coverage on a changing index, sort by id is our best bet
            q["sort"] = [{"id" : {"order" : "asc"}}]
        counter = 0
        while True:
            # apply the limit
            if limit is not None and counter >= limit:
                break

            res = cls.query(q=q)
            rs = [r.get("_source") if "_source" in r else r.get("fields") for r in res.get("hits", {}).get("hits", [])]
            # print counter, len(rs), res.get("hits", {}).get("total"), len(res.get("hits", {}).get("hits", [])), json.dumps(q)
            if len(rs) == 0:
                break
            for r in rs:
                # apply the limit (again)
                if limit is not None and counter >= limit:
                    break
                counter += 1
                if wrap:
                    yield cls(**r)
                else:
                    yield r
            q["from"] += page_size

    @classmethod
    def iterall(cls, page_size=1000, limit=None):
        return cls.iterate(deepcopy(all_query), page_size, limit)


class Article(DomainObject):
    __type__ = "article"

    def bibjson(self):
        if "bibjson" not in self.data:
            self.data["bibjson"] = {}
        return ArticleBibJSON(self.data.get("bibjson"))

    def set_bibjson(self, bibjson):
        bibjson = bibjson.bibjson if isinstance(bibjson, ArticleBibJSON) else bibjson
        self.data["bibjson"] = bibjson

    def history(self):
        hs = self.data.get("history", [])
        tuples = []
        for h in hs:
            tuples.append((h.get("date"), ArticleBibJSON(h.get("bibjson"))))
        return tuples

    def _generate_index(self):
        # the index fields we are going to generate
        issns = []
        subjects = []
        schema_subjects = []
        schema_codes = []
        classification = []
        langs = []
        country = None
        license = []
        publisher = []

        # the places we're going to get those fields from
        cbib = self.bibjson()
        jindex = self.data.get('index', {})
        hist = self.history()

        # get the issns out of the current bibjson
        issns += cbib.get_identifiers(cbib.P_ISSN)
        issns += cbib.get_identifiers(cbib.E_ISSN)

        # now get the issns out of the historic records
        for date, hbib in hist:
            issns += hbib.get_identifiers(hbib.P_ISSN)
            issns += hbib.get_identifiers(hbib.E_ISSN)

        # get the subjects and concatenate them with their schemes from the current bibjson
        for subs in cbib.subjects():
            scheme = subs.get("scheme")
            term = subs.get("term")
            subjects.append(term)
            schema_subjects.append(scheme + ":" + term)
            classification.append(term)
            if "code" in subs:
                schema_codes.append(scheme + ":" + subs.get("code"))

        # copy the languages
        if cbib.journal_language is not None:
            langs = cbib.journal_language

        # copy the country
        if jindex.get('country'):
            country = jindex.get('country')
        elif cbib.journal_country:
            pass
            #country = xwalk.get_country_name(cbib.journal_country)

        # get the title of the license
        lic = cbib.get_journal_license()
        if lic is not None:
            license.append(lic.get("title"))

        # copy the publisher/provider
        if cbib.publisher:
            publisher.append(cbib.publisher)

        # deduplicate the list
        issns = list(set(issns))
        subjects = list(set(subjects))
        schema_subjects = list(set(schema_subjects))
        classification = list(set(classification))
        license = list(set(license))
        publisher = list(set(publisher))
        langs = list(set(langs))
        schema_codes = list(set(schema_codes))

        # work out what the date of publication is
        date = cbib.get_publication_date()

        # build the index part of the object
        self.data["index"] = {}
        if len(issns) > 0:
            self.data["index"]["issn"] = issns
        if date != "":
            self.data["index"]["date"] = date
        if len(subjects) > 0:
            self.data["index"]["subject"] = subjects
        if len(schema_subjects) > 0:
            self.data["index"]["schema_subject"] = schema_subjects
        if len(classification) > 0:
            self.data["index"]["classification"] = classification
        if len(publisher) > 0:
            self.data["index"]["publisher"] = publisher
        if len(license) > 0:
            self.data["index"]["license"] = license
        if len(langs) > 0:
            self.data["index"]["language"] = langs
        if country is not None:
            self.data["index"]["country"] = country
        if schema_codes > 0:
            self.data["index"]["schema_code"] = schema_codes

    def prep(self):
        self._generate_index()
        self.data['last_updated'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    def save(self):
        self._generate_index()
        super(Article, self).save()

all_query = {
    "query" : {
        "match_all" : { }
    }
}
