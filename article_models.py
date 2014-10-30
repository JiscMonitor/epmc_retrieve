
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
        t = str(app.config['ELASTIC_SEARCH_HOST']).rstrip('/') + '/'
        t += app.config['ELASTIC_SEARCH_DB'] + '/'
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

            except requests.exceptions.ConnectionError:
                attempt += 1

            # wait before retrying
            time.sleep((2**attempt) * back_off_factor)

    def save_from_form(self,request):
        newdata = request.json if request.json else request.values
        for k, v in newdata.items():
            if k not in ['submit']:
                self.data[k] = v
        self.save()

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

    @classmethod
    def pull_by_key(cls, key, value):
        res = cls.query(q={"query":{"term":{key+app.config['FACET_FIELD']:value}}})
        if res.get('hits',{}).get('total',0) == 1:
            return cls.pull( res['hits']['hits'][0]['_source']['id'] )
        else:
            return None

    @classmethod
    def keys(cls,mapping=False,prefix=''):
        # return a sorted list of all the keys in the index
        if not mapping:
            mapping = cls.query(endpoint='_mapping')[cls.__type__]['properties']
        keys = []
        for item in mapping:
            if mapping[item].has_key('fields'):
                for item in mapping[item]['fields'].keys():
                    if item != 'exact' and not item.startswith('_'):
                        keys.append(prefix + item + app.config['FACET_FIELD'])
            else:
                keys = keys + cls.keys(mapping=mapping[item]['properties'],prefix=prefix+item+'.')
        keys.sort()
        return keys

    @staticmethod
    def make_query(recid='', endpoint='_search', q='', terms=None, facets=None, should_terms=None, **kwargs):
        '''
        Generate a query object based on parameters but don't sent to
        backend - return it instead. Must always have the same
        parameters as the query method. See query method for explanation
        of parameters.
        '''
        if recid and not recid.endswith('/'): recid += '/'
        if isinstance(q,dict):
            query = q
            if 'bool' not in query['query']:
                boolean = {'bool':{'must': [] }}
                boolean['bool']['must'].append( query['query'] )
                query['query'] = boolean
            if 'must' not in query['query']['bool']:
                query['query']['bool']['must'] = []
        elif q:
            query = {
                'query': {
                    'bool': {
                        'must': [
                            {'query_string': { 'query': q }}
                        ]
                    }
                }
            }
        else:
            query = {
                'query': {
                    'bool': {
                        'must': [
                            {'match_all': {}}
                        ]
                    }
                }
            }

        if facets:
            if 'facets' not in query:
                query['facets'] = {}
            for k, v in facets.items():
                query['facets'][k] = {"terms":v}

        if terms:
            boolean = {'must': [] }
            for term in terms:
                if not isinstance(terms[term],list): terms[term] = [terms[term]]
                for val in terms[term]:
                    obj = {'term': {}}
                    obj['term'][ term ] = val
                    boolean['must'].append(obj)
            if q and not isinstance(q,dict):
                boolean['must'].append( {'query_string': { 'query': q } } )
            elif q and 'query' in q:
                boolean['must'].append( query['query'] )
            query['query'] = {'bool': boolean}

        # FIXME: this may only work if a term is also supplied above - code is a bit tricky to read
        if should_terms is not None and len(should_terms) > 0:
            for s in should_terms:
                if not isinstance(should_terms[s],list): should_terms[s] = [should_terms[s]]
                query["query"]["bool"]["must"].append({"terms" : {s : should_terms[s]}})

        for k,v in kwargs.items():
            if k == '_from':
                query['from'] = v
            else:
                query[k] = v
        # print json.dumps(query)
        return query

    @classmethod
    def query(cls, recid='', endpoint='_search', q='', terms=None, facets=None, **kwargs):
        '''Perform a query on backend.

        :param recid: needed if endpoint is about a record, e.g. mlt
        :param endpoint: default is _search, but could be _mapping, _mlt, _flt etc.
        :param q: maps to query_string parameter if string, or query dict if dict.
        :param terms: dictionary of terms to filter on. values should be lists.
        :param facets: dict of facets to return from the query.
        :param kwargs: any keyword args as per
            http://www.elasticsearch.org/guide/reference/api/search/uri-request.html
        '''
        query = cls.make_query(recid, endpoint, q, terms, facets, **kwargs)
        return cls.send_query(query, endpoint=endpoint, recid=recid)


    @classmethod
    def send_query(cls, qobj, endpoint='_search', recid='', retry=50):
        '''Actually send a query object to the backend.'''
        r = None
        count = 0
        exception = None
        while count < retry:
            count += 1
            try:
                if endpoint in ['_mapping']:
                    r = requests.get(cls.target() + recid + endpoint)
                else:
                    r = requests.post(cls.target() + recid + endpoint, data=json.dumps(qobj))
                break
            except Exception as e:
                exception = e
            time.sleep(0.5)

        if r is not None:
            return r.json()
        if exception is not None:
            raise exception
        raise Exception("Couldn't get the ES query endpoint to respond.  Also, you shouldn't be seeing this.")

    def accessed(self):
        if 'last_access' not in self.data:
            self.data['last_access'] = []
        try:
            usr = current_user.id
        except:
            usr = "anonymous"
        self.data['last_access'].insert(0, { 'user':usr, 'date':datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ") } )
        r = requests.put(self.target() + self.data['id'], data=json.dumps(self.data))

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

    def csv(self, multival_sep=','):
        raise NotImplementedError

    @classmethod
    def prefix_query(cls, field, prefix, size=5):
        # example of a prefix query
        # {
        #     "query": {"prefix" : { "bibjson.publisher" : "ope" } },
        #     "size": 0,
        #     "facets" : {
        #       "publisher" : { "terms" : {"field" : "bibjson.publisher.exact", "size": 5} }
        #     }
        # }
        if field.endswith(app.config['FACET_FIELD']):
            # strip .exact (or whatever it's configured as) off the end
            query_field = field[:field.rfind(app.config['FACET_FIELD'])]
        else:
            query_field = field

        # the actual terms should come from the .exact version of the
        # field - we are suggesting whole values, not fragments
        facet_field = query_field + app.config['FACET_FIELD']

        q = {
            "query": {"prefix" : { query_field : prefix.lower() } },
            "size": 0,
            "facets" : {
              field : { "terms" : {"field" : facet_field, "size": size} }
            }
        }

        return cls.send_query(q)

    @classmethod
    def autocomplete(cls, field, prefix, size=5):
        res = cls.prefix_query(field, prefix, size=size)
        result = []
        for term in res['facets'][field]['terms']:
            # keep ordering - it's by count by default, so most frequent
            # terms will now go to the front of the result list
            result.append({"id": term['term'], "text": term['term']})
        return result




class Article(DomainObject):
    __type__ = "article"

    @classmethod
    def duplicates(cls, issns=None, publisher_record_id=None, doi=None, fulltexts=None, title=None, volume=None, number=None, start=None, should_match=None):
        # some input sanitisation
        issns = issns if isinstance(issns, list) else []
        urls = fulltexts if isinstance(fulltexts, list) else [fulltexts] if isinstance(fulltexts, str) or isinstance(fulltexts, unicode) else []

        q = DuplicateArticleQuery(issns=issns,
                                    publisher_record_id=publisher_record_id,
                                    doi=doi,
                                    urls=urls,
                                    title=title,
                                    volume=volume,
                                    number=number,
                                    start=start,
                                    should_match=should_match)
        # print json.dumps(q.query())

        res = cls.query(q=q.query())
        articles = [cls(**hit.get("_source")) for hit in res.get("hits", {}).get("hits", [])]
        return articles

    @classmethod
    def list_volumes(cls, issns):
        q = ArticleVolumesQuery(issns)
        result = cls.query(q=q.query())
        return [t.get("term") for t in result.get("facets", {}).get("vols", {}).get("terms", [])]

    @classmethod
    def get_by_volume(cls, issns, volume):
        q = ArticleQuery(issns=issns, volume=volume)
        articles = cls.iterate(q.query(), page_size=1000)
        return articles

    @classmethod
    def find_by_issns(cls, issns):
        q = ArticleQuery(issns=issns)
        articles = cls.iterate(q.query(), page_size=1000)
        return articles

    @classmethod
    def delete_selected(cls, query=None, owner=None, snapshot=True):
        if owner is not None:
            from portality.models import Journal
            issns = Journal.issns_by_owner(owner)
            q = ArticleQuery(issns=issns)
            query = q.query()

        if snapshot:
            articles = cls.iterate(query, page_size=1000)
            for article in articles:
                article.snapshot()

        cls.delete_by_query(query)

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

    def snapshot(self):
        from portality.models import ArticleHistory

        snap = deepcopy(self.data)
        if "id" in snap:
            snap["about"] = snap["id"]
            del snap["id"]
        if "index" in snap:
            del snap["index"]
        if "last_updated" in snap:
            del snap["last_updated"]
        if "created_date" in snap:
            del snap["created_date"]

        hist = ArticleHistory(**snap)
        hist.save()

        # FIXME: make this use the article history class
        #snap = deepcopy(self.data.get("bibjson"))
        #self.add_history(snap)

    def add_history(self, bibjson, date=None):
        """Deprecated"""
        bibjson = bibjson.bibjson if isinstance(bibjson, ArticleBibJSON) else bibjson
        if date is None:
            date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        snobj = {"date" : date, "bibjson" : bibjson}
        if "history" not in self.data:
            self.data["history"] = []
        self.data["history"].append(snobj)

    def is_in_doaj(self):
        return self.data.get("admin", {}).get("in_doaj", False)

    def set_in_doaj(self, value):
        if "admin" not in self.data:
            self.data["admin"] = {}
        self.data["admin"]["in_doaj"] = value

    def publisher_record_id(self):
        return self.data.get("admin", {}).get("publisher_record_id")

    def set_publisher_record_id(self, pri):
        if "admin" not in self.data:
            self.data["admin"] = {}
        self.data["admin"]["publisher_record_id"] = pri

    def upload_id(self):
        return self.data.get("admin", {}).get("upload_id")

    def set_upload_id(self, uid):
        if "admin" not in self.data:
            self.data["admin"] = {}
        self.data["admin"]["upload_id"] = uid

    def merge(self, old, take_id=True):
        # this takes an old version of the article and brings
        # forward any useful information that is needed.  The rules of merge are:
        # - ignore "index" (it gets regenerated on save)
        # - always take the "created_date"
        # - any top level field that does not exist in the current item (esp "id" and "history")
        # - in "admin", copy any field that does not already exist

        # first thing to do is create a snapshot of the old record
        old.snapshot()

        # now go on and do the merge

        # always take the created date
        self.set_created(old.created_date)

        # take the id
        if self.id is None or take_id:
            self.set_id(old.id)

        # take the history (deprecated)
        if len(self.data.get("history", [])) == 0:
            self.data["history"] = deepcopy(old.data.get("history", []))

        # take the bibjson
        if "bibjson" not in self.data:
            self.set_bibjson(deepcopy(old.bibjson()))

        # take the admin if there isn't one
        if "admin" not in self.data:
            self.data["admin"] = deepcopy(old.data.get("admin", {}))
        else:
            # otherwise, copy any admin keys that don't exist on the current item
            oa = old.data.get("admin", {})
            for key in oa:
                if key not in self.data["admin"]:
                    self.data["admin"][key] = deepcopy(oa[key])

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
            country = xwalk.get_country_name(cbib.journal_country)

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

            except requests.exceptions.ConnectionError:
                attempt += 1

            # wait before retrying
            time.sleep((2**attempt) * back_off_factor)
