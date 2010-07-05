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
import logging
import re
from datetime import datetime, tzinfo, timedelta
from BeautifulSoup import BeautifulSoup, SoupStrainer
from models import Seminar
from icalendar import Calendar, Event


class SGT(tzinfo):
    "Time zone for Singapore"

    def utcoffset(self, dt):
        return timedelta(hours=8)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "Asia/Singapore"


class UpdateHandler(webapp.RequestHandler):
    def get(self):
        # Read HTML from seminar page.
        url = "http://www.comp.nus.edu.sg/cs/csseminar.html"
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
        split_time = re.compile("(.*) - (.*)")
        entries = SoupStrainer('tr', bgcolor="#FFFFFF")
        soup = BeautifulSoup(result.content,
                             parseOnlyThese=entries)
        start = ""
        end = ""
        url = ""
        title = ""
        speaker = ""
        for row in soup:
            try:
                dt = row.contents[0].p
                date = unicode(dt.contents[0].extract())
                time = unicode(dt.contents[1].extract())
                m = split_time.search(time)
                start = " ".join([date, m.group(1)])
                end = " ".join([date, m.group(2)])

                info = row.contents[1].p
                url = info.a['href']
                title = unicode(info.a.string.extract())
                speaker = info.getText(separator="\n") # rest are speaker info
            except Exception, e:
                logging.error("%s @ %s" % (e, url))
                continue

            # check if already exist
            q = Seminar.gql("WHERE url = :url", url=url)
            if q.count() > 0:
                continue

            # convert date time.
            # sample: July 16, 2010 10.00am
            sgt = SGT()
            try:
                start = datetime.strptime(start, "%B %d, %Y %I.%M%p")
                start = start.replace(tzinfo=sgt)
                end = datetime.strptime(end, "%B %d, %Y %I.%M%p")
                end = end.replace(tzinfo=sgt)
            except ValueError, e:
                logging.error("%s @ %s" % (e, url))
                continue

            s = Seminar(
                start = start,
                end = end,
                title = title,
                speaker = speaker,
                url = url
                )

            deferred.defer(s.fetch_and_put)


class NusCsHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = "text/calendar; charset=utf-8"

        cal = Calendar()
        cal.add('prodid', '-//NUS CS Seminars//ronhuang.org//')
        cal.add('version', '2.0')
        cal.add('X-WR-CALNAME', 'NUS CS Seminars')
        cal.add('X-WR-CALDESC', "Seminars are open to the public, and usually held in the School's Seminar Room.")

        q = Seminar.all().order('start')
        for s in q:
            event = Event()
            event['uid'] = s.url
            event.add('summary', s.title)
            event.add('dtstart', s.start)
            event.add('dtend', s.end)
            event.add('dtstamp', s.stamp)
            event.add('location', s.venue)
            event.add('url', s.url)
            event.add('description', s.intro)
            event.add('comment', s.speaker)
            event.add('categories', 'seminar')
            event.add('class', 'PUBLIC')

            cal.add_component(event)

        self.response.out.write(cal.as_string())


def main():
    actions = [
        ('/calennar/update', UpdateHandler),
        ('/calennar/nuscs.ics', NusCsHandler),
        ]
    application = webapp.WSGIApplication(actions, debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
