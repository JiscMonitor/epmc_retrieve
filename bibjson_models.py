
class GenericBibJSON(object):
    # vocab of known identifier types
    P_ISSN = "pissn"
    E_ISSN = "eissn"
    DOI = "doi"

    # allowable values for the url types
    HOMEPAGE = "homepage"
    WAIVER_POLICY = "waiver_policy"
    EDITORIAL_BOARD = "editorial_board"
    AIMS_SCOPE = "aims_scope"
    AUTHOR_INSTRUCTIONS = "author_instructions"
    OA_STATEMENT = "oa_statement"
    FULLTEXT = "fulltext"

    # constructor
    def __init__(self, bibjson=None):
        self.bibjson = bibjson if bibjson is not None else {}

    # generic property getter and setter for ad-hoc extensions
    def get_property(self, prop):
        return self.bibjson.get(prop)

    def set_property(self, prop, value):
        self.bibjson[prop] = value

    # shared simple property getter and setters

    @property
    def title(self): return self.bibjson.get("title")
    @title.setter
    def title(self, val) : self.bibjson["title"] = val

    # complex getters and setters

    def _normalise_identifier(self, idtype, value):
        if idtype in [self.P_ISSN, self.E_ISSN]:
            return self._normalise_issn(value)
        return value

    def _normalise_issn(self, issn):
        issn = issn.upper()
        if len(issn) > 8: return issn
        if len(issn) == 8:
            if "-" in issn: return "0" + issn
            else: return issn[:4] + "-" + issn[4:]
        if len(issn) < 8:
            if "-" in issn: return ("0" * (9 - len(issn))) + issn
            else:
                issn = ("0" * (8 - len(issn))) + issn
                return issn[:4] + "-" + issn[4:]

    def add_identifier(self, idtype, value):
        if "identifier" not in self.bibjson:
            self.bibjson["identifier"] = []
        idobj = {"type" : idtype, "id" : self._normalise_identifier(idtype, value)}
        self.bibjson["identifier"].append(idobj)

    def get_identifiers(self, idtype=None):
        if idtype is None:
            return self.bibjson.get("identifier", [])

        ids = []
        for identifier in self.bibjson.get("identifier", []):
            if identifier.get("type") == idtype and identifier.get("id") not in ids:
                ids.append(identifier.get("id"))
        return ids

    def get_one_identifier(self, idtype=None):
        results = self.get_identifiers(idtype=idtype)
        if results:
            return results[0]
        else:
            return None

    def update_identifier(self, idtype, new_value):
        if not new_value:
            self.remove_identifiers(idtype=idtype)
            return

        if 'identifier' not in self.bibjson:
            return

        if not self.get_one_identifier(idtype):
            self.add_identifier(idtype, new_value)
            return

        # so an old identifier does actually exist, and we actually want
        # to update it
        for id_ in self.bibjson['identifier']:
            if id_['type'] == idtype:
                id_['id'] = new_value

    def remove_identifiers(self, idtype=None, id=None):
        # if we are to remove all identifiers, this is easy
        if idtype is None and id is None:
            self.bibjson["identifier"] = []
            return

        # else, find all the identifiers positions that we need to remove
        idx = 0
        remove = []
        for identifier in self.bibjson.get("identifier", []):
            if idtype is not None and id is None:
                if identifier.get("type") == idtype:
                    remove.append(idx)
            elif idtype is None and id is not None:
                if identifier.get("id") == id:
                    remove.append(idx)
            else:
                if identifier.get("type") == idtype and identifier.get("id") == id:
                    remove.append(idx)
            idx += 1

        # sort the positions of the ids to remove, largest first
        remove.sort(reverse=True)

        # now remove them one by one (having the largest first means the lower indices
        # are not affected
        for i in remove:
            del self.bibjson["identifier"][i]

    @property
    def keywords(self):
        return self.bibjson.get("keywords", [])

    def add_keyword(self, keyword):
        if "keywords" not in self.bibjson:
            self.bibjson["keywords"] = []
        self.bibjson["keywords"].append(keyword)

    def set_keywords(self, keywords):
        self.bibjson["keywords"] = keywords

    def add_url(self, url, urltype=None, content_type=None):
        if not url:
            # do not add empty URL-s
            return

        if "link" not in self.bibjson:
            self.bibjson["link"] = []
        urlobj = {"url" : url}
        if urltype is not None:
            urlobj["type"] = urltype
        if content_type is not None:
            urlobj["content_type"] = content_type
        self.bibjson["link"].append(urlobj)

    def get_urls(self, urltype=None):
        if urltype is None:
            return self.bibjson.get("link", [])

        urls = []
        for link in self.bibjson.get("link", []):
            if link.get("type") == urltype:
                urls.append(link.get("url"))
        return urls

    def get_single_url(self, urltype):
        urls = self.get_urls(urltype=urltype)
        if urls:
            return urls[0]
        return None

    def update_url(self, url, urltype=None):
        if "link" not in self.bibjson:
            self.bibjson['link'] = []

        urls = self.bibjson['link']

        if urls:
            for u in urls: # do not reuse "url" as it's a parameter!
                if u['type'] == urltype:
                    u['url'] = url
        else:
            self.add_url(url, urltype)

    def add_subject(self, scheme, term, code=None):
        if "subject" not in self.bibjson:
            self.bibjson["subject"] = []
        sobj = {"scheme" : scheme, "term" : term}
        if code is not None:
            sobj["code"] = code
        self.bibjson["subject"].append(sobj)

    def subjects(self):
        return self.bibjson.get("subject", [])

    def set_subjects(self, subjects):
        self.bibjson["subject"] = subjects

    def remove_subjects(self):
        if "subject" in self.bibjson:
            del self.bibjson["subject"]


class ArticleBibJSON(GenericBibJSON):

    # article-specific simple getters and setters
    @property
    def year(self): return self.bibjson.get("year")
    @year.setter
    def year(self, val) : self.bibjson["year"] = str(val)
    @year.deleter
    def year(self):
        if "year" in self.bibjson:
            del self.bibjson["year"]

    @property
    def month(self): return self.bibjson.get("month")
    @month.setter
    def month(self, val) : self.bibjson["month"] = str(val)
    @month.deleter
    def month(self):
        if "month" in self.bibjson:
            del self.bibjson["month"]

    @property
    def start_page(self): return self.bibjson.get("start_page")
    @start_page.setter
    def start_page(self, val) : self.bibjson["start_page"] = val

    @property
    def end_page(self): return self.bibjson.get("end_page")
    @end_page.setter
    def end_page(self, val) : self.bibjson["end_page"] = val

    @property
    def abstract(self): return self.bibjson.get("abstract")
    @abstract.setter
    def abstract(self, val) : self.bibjson["abstract"] = val

    # article-specific complex part getters and setters

    def _set_journal_property(self, prop, value):
        if "journal" not in self.bibjson:
            self.bibjson["journal"] = {}
        self.bibjson["journal"][prop] = value

    @property
    def volume(self):
        return self.bibjson.get("journal", {}).get("volume")

    @volume.setter
    def volume(self, value):
        self._set_journal_property("volume", value)

    @property
    def number(self):
        return self.bibjson.get("journal", {}).get("number")

    @number.setter
    def number(self, value):
        self._set_journal_property("number", value)

    @property
    def journal_title(self):
        return self.bibjson.get("journal", {}).get("title")

    @journal_title.setter
    def journal_title(self, title):
        self._set_journal_property("title", title)

    @property
    def journal_language(self):
        return self.bibjson.get("journal", {}).get("language")

    @journal_language.setter
    def journal_language(self, lang):
        self._set_journal_property("language", lang)

    # beware, the index part of an article will contain the same as the
    # index part of a journal, not the same as the bibjson part of a
    # journal!
    # the method below is referring to the bibjson part of a journal
    @property
    def journal_country(self):
        return self.bibjson.get("journal", {}).get("country")

    @journal_country.setter
    def journal_country(self, country):
        self._set_journal_property("country", country)

    @property
    def publisher(self):
        return self.bibjson.get("journal", {}).get("publisher")

    @publisher.setter
    def publisher(self, value):
        self._set_journal_property("publisher", value)

    def add_author(self, name, email=None, affiliation=None):
        if "author" not in self.bibjson:
            self.bibjson["author"] = []
        aobj = {"name" : name}
        if email is not None:
            aobj["email"] = email
        if affiliation is not None:
            aobj["affiliation"] = affiliation
        self.bibjson["author"].append(aobj)

    @property
    def author(self):
        return self.bibjson.get("author", [])

    def set_journal_license(self, licence_title, licence_type, url=None, version=None, open_access=None):
        lobj = {"title" : licence_title, "type" : licence_type}
        if url is not None:
            lobj["url"] = url
        if version is not None:
            lobj["version"] = version
        if open_access is not None:
            lobj["open_access"] = open_access

        self._set_journal_property("license", [lobj])

    def get_journal_license(self):
        return self.bibjson.get("journal", {}).get("license", [None])[0]

    def get_publication_date(self):
        # work out what the date of publication is
        date = ""
        if self.year is not None:
            # fix 2 digit years
            if len(self.year) == 2:
                if int(self.year) <=13:
                    self.year = "20" + self.year
                else:
                    self.year = "19" + self.year

            # if we still don't have a 4 digit year, forget it
            if len(self.year) != 4:
                return date

            # build up our proposed datestamp
            date += str(self.year)
            if self.month is not None:
                try:
                    if len(self.month) == 1:
                        date += "-0" + str(self.month)
                    else:
                        date += "-" + str(self.month)
                except:
                    # FIXME: months are in all sorts of forms, we can only handle
                    # numeric ones right now
                    date += "-01"
            else:
                date += "-01"
            date += "-01T00:00:00Z"

            # attempt to confirm the format of our datestamp
            try:
                datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
            except:
                return ""
        return date

    def remove_journal_metadata(self):
        if "journal" in self.bibjson:
            del self.bibjson["journal"]
