#!/usr/bin/env python
#
# Copyright (c) 2010 Ron Huang
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import urlfetch
from google.appengine.ext import deferred
from google.appengine.api import memcache
from google.appengine.runtime import DeadlineExceededError
import logging
import re
from datetime import datetime, timedelta
from models import Seminar, Cache
from icalendar import Calendar, Event
import utils
import chardet
from sgmllib import SGMLParser
import htmlentitydefs


SGT = utils.SGT()
SPLIT_TIME = re.compile("(.*) - (.*)")

STATE_DATE = 1
STATE_TIME = 2
STATE_TITLE = 3
STATE_SPEAKER = 4


class NusCsParser(SGMLParser):
    def reset(self):
        SGMLParser.reset(self)
        self._in_entry = None
        self._state = None
        self._smnr = None

    def unknown_starttag(self, tag, attrs):
        if tag == "tr":
            self._in_entry = True
            self._state = STATE_DATE
            self._smnr = {}
        elif self._in_entry and tag == "a":
            for key, value in attrs:
                if key == "href":
                    self._smnr['url'] = value
                    break
        elif self._in_entry and self._state == STATE_SPEAKER and tag == "br":
            if 'speaker' not in self._smnr:
                self._smnr['speaker'] = []
            self._smnr['speaker'].append("\n")

    def unknown_endtag(self, tag):
        if self._in_entry and self._state == STATE_SPEAKER and tag == "td":
            self._in_entry = None
            if "url" not in self._smnr or \
                    "date" not in self._smnr or \
                    "time" not in self._smnr or \
                    "title" not in self._smnr or \
                    "speaker" not in self._smnr:
                # might not be in the correct <tr>
                return

            # check if already exist
            url = self._smnr['url']
            exist = memcache.get(url)
            if exist:
                return
            q = Seminar.gql("WHERE url = :url", url=url)
            if q.count() > 0:
                memcache.add(url, True)
                return

            # start and end time
            date = self._smnr['date']
            time = self._smnr['time']

            m = SPLIT_TIME.search(time)
            if not m:
                # might not be in the correct <tr>
                return

            start = m.group(1)
            end = m.group(2)
            try:
                # convert time
                # sample: July 16, 2010 10.00am
                start = " ".join([date, start])
                start = datetime.strptime(start, "%B %d, %Y %I.%M%p")
                start = start.replace(tzinfo=SGT)
                end = " ".join([date, end])
                end = datetime.strptime(end, "%B %d, %Y %I.%M%p")
                end = end.replace(tzinfo=SGT)
            except Exception, e:
                # might not be in the correct <tr>
                logging.error("%s @ %s" % (e, url))
                return

            # title
            title = "".join(self._smnr['title'])
            if len(title) > 0:
                e = chardet.detect(title)["encoding"]
                title = unicode(title, e)
            title = utils.unescape(title)

            # speaker
            sp = self._smnr['speaker']
            while len(sp) > 0 and sp[0] == "\n":
                sp.pop(0)
            speaker = "".join(sp)
            if len(speaker) > 0:
                e = chardet.detect(speaker)["encoding"]
                speaker = unicode(speaker, e)
            speaker = utils.unescape(speaker)

            # create model
            s = Seminar(
                start = start,
                end = end,
                title = title,
                speaker = speaker,
                url = url,
                )
            deferred.defer(s.fetch_and_put)

        elif self._in_entry and tag == "a":
            if self._state == STATE_TITLE:
                self._state = STATE_SPEAKER

    def handle_data(self, text):
        if self._in_entry:
            if self._state == STATE_DATE:
                self._smnr['date'] = text
                self._state = STATE_TIME
            elif self._state == STATE_TIME:
                self._smnr['time'] = text
                self._state = STATE_TITLE
            elif self._state == STATE_TITLE:
                if 'title' not in self._smnr:
                    self._smnr['title'] = []
                self._smnr['title'].append(text)
            else: # rest are STATE_SPEAKER
                if 'speaker' not in self._smnr:
                    self._smnr['speaker'] = []
                self._smnr['speaker'].append(text)

    def handle_charref(self, ref):
        if self._in_entry and (self._state == STATE_TITLE or self._state == STATE_SPEAKER):
            # called for each character reference, e.g. for "&#160;", ref will be "160"
            # Reconstruct the original character reference.
            text = "&#%(ref)s;" % locals()

            if self._state == STATE_TITLE:
                if 'title' not in self._smnr:
                    self._smnr['title'] = []
                self._smnr['title'].append(text)
            elif self._state == STATE_SPEAKER:
                if 'speaker' not in self._smnr:
                    self._smnr['speaker'] = []
                self._smnr['speaker'].append(text)

    def handle_entityref(self, ref):
        if self._in_entry and (self._state == STATE_TITLE or self._state == STATE_SPEAKER):
            # called for each entity reference, e.g. for "&copy;", ref will be "copy"
            # Reconstruct the original entity reference.
            # standard HTML entities are closed with a semicolon; other entities are not
            text = None
            if htmlentitydefs.entitydefs.has_key(ref):
                text = "&%(ref)s;" % locals()
            else:
                text = "&%(ref)s" % locals()

            if self._state == STATE_TITLE:
                if 'title' not in self._smnr:
                    self._smnr['title'] = []
                self._smnr['title'].append(text)
            elif self._state == STATE_SPEAKER:
                if 'speaker' not in self._smnr:
                    self._smnr['speaker'] = []
                self._smnr['speaker'].append(text)

    def getUrl(self):
        if self._in_entry and "url" in self._smnr:
            return self._smnr["url"]
        else:
            return "N/A"


class UpdateHandler(webapp.RequestHandler):
    def get(self):
        # Read HTML from seminar page.
        url = "https://mysoc.nus.edu.sg/~cmsem/seminar_files/"
        result = None
        try:
            result = urlfetch.fetch(url)
        except urlfetch.InvalidURLError, e:
            logging.error(e)
            self.error(500)
        except urlfetch.DownloadError, e:
            logging.error(e)
            self.error(500)
        except urlfetch.ResponseTooLargeError, e:
            logging.error(e)
            self.error(500)
        except:
            self.error(500)

        if result.status_code != 200:
            self.error(result.status_code)

        # Parse content of the page.
        p = NusCsParser()
        try:
            p.feed(result.content)
        except DeadlineExceededError, e:
            logging.warning("Only made to %s" % p.getUrl())
        finally:
            p.close()


class NusCsHandler(webapp.RequestHandler):
    def get(self, year='current'):
        """year can be 'all', 'current', '2002', '2011', etc."""

        self.response.headers['Content-Type'] = "text/calendar; charset=utf-8"

        # find from cache
        q = Cache.gql("WHERE site = :site AND year = :year", site="nuscs", year=year)
        c = q.get()
        if c:
            self.response.out.write(c.data)
            return

        # generate now
        cal = Calendar()
        cal.add('prodid', '-//NUS CS Seminars//ronhuang.org//')
        cal.add('version', '2.0')
        cal.add('X-WR-CALNAME', 'NUS CS Seminars')
        cal.add('X-WR-CALDESC', "Seminars are open to the public, and usually held in the School's Seminar Room.")

        q = Seminar.all().order('start')
        if year != "all":
            yn = None
            try:
                yn = int(year)
            except:
                pass

            if yn:
                # return events within that year
                q = q.filter("start >=", datetime(yn, 1, 1, tzinfo=SGT))
                q = q.filter("start <", datetime(yn + 1, 1, 1, tzinfo=SGT))
            else: #default
                # return a year of events.
                q = q.filter("start >=", datetime.now(SGT) - timedelta(days=366))

        for s in q:
            event = Event()
            event['uid'] = s.url
            event.add('summary', s.title)
            event.add('dtstart', s.start)
            event.add('dtend', s.end)
            event.add('dtstamp', s.stamp)
            event.add('location', s.venue)
            event.add('url', s.url)
            event.add('description', s.speaker)
            event.add('categories', 'seminar')
            event.add('class', 'PUBLIC')

            cal.add_component(event)

        # generated data
        data = cal.as_string()
        encoding = chardet.detect(data)['encoding']
        data = unicode(data, encoding)

        # store in datastore
        q = Cache.gql("WHERE site = :site AND year = :year", site="nuscs", year=year)
        c = q.get()
        if c:
            c.data = data
        else:
            c = Cache(site = "nuscs", data = data, year = year)
        c.put()

        self.response.out.write(data)


def main():
    actions = [
        ('/calennar/update$', UpdateHandler),
        ('/calennar/nuscs.ics$', NusCsHandler),
        ('/calennar/nuscs-(all|current|[0-9]+).ics$', NusCsHandler),
        ]
    application = webapp.WSGIApplication(actions, debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
