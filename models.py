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


from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.api import memcache
from icalendar import UTC
from datetime import datetime
import logging
import re
import chardet


DOS2UNIX = re.compile("\r\n", re.M)
LTRIM_G = re.compile("\n[ \t]+", re.M)
EXTRACT_VENUE = re.compile("^VENUE\s*:\s*(?P<venue>.+?)\n\n", re.M | re.S | re.I)


class Cache(db.Model):
    site = db.StringProperty(required=True)
    data = db.TextProperty(required=True)


class Seminar(db.Model):
    url = db.LinkProperty(required=True)
    start = db.DateTimeProperty(required=True)
    end = db.DateTimeProperty(required=True)
    stamp = db.DateTimeProperty(auto_now_add=True)
    title = db.StringProperty(required=True)
    speaker = db.TextProperty(required=True)
    venue = db.StringProperty(multiline=True)

    def fetch_and_put(self):
        # fetch
        result = None
        try:
            result = urlfetch.fetch(self.url)
        except Exception, e:
            logging.warning("%s @ %s" % (e, self.url))

        # check status code
        if result and result.status_code != 200:
            logging.warning("Returned %s when fetching %s" % (result.status_code, self.url))

        # get last-modified as stamp
        if result and result.headers and ('last-modified' in result.headers):
            stamp = result.headers['last-modified']
            stamp = datetime.strptime(stamp, '%a, %d %b %Y %H:%M:%S %Z')
            stamp = stamp.replace(tzinfo=UTC)
            self.stamp = stamp

        # detect encoding
        s = result and result.content or ""
        try:
            encoding = chardet.detect(s)['encoding']
            s = unicode(s, encoding)
        except Exception, e:
            logging.warning("%s @ %s" % (e, self.url))

        # dos2unix
        s = DOS2UNIX.sub("\n", s)
        # trim space in front of each line
        s = LTRIM_G.sub("\n", s)

        # Extract venue
        m = EXTRACT_VENUE.search(s)
        if m:
            self.venue = m.group("venue").strip()
        else:
            logging.warning("Can't retrive venue from %s\n%s" % (self.url, s))

        self.put()
        memcache.set("nuscs_up_to_date", False)


class TweetAccessToken(db.Model):
    name = db.StringProperty(required=True)
    stamp = db.DateTimeProperty(auto_now=True)
    clavis = db.StringProperty(required=True)
    arcanum = db.TextProperty(required=True)
