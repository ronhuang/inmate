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
import logging
import re
import chardet


class Seminar(db.Model):
    url = db.LinkProperty(required=True)
    start = db.DateTimeProperty(required=True)
    end = db.DateTimeProperty(required=True)
    title = db.StringProperty(required=True)
    speaker = db.TextProperty(required=True)
    venue = db.StringProperty(multiline=True)
    info = db.TextProperty()

    def fetch_and_put(self):
        result = None
        try:
            result = urlfetch.fetch(self.url)
        except Exception, e:
            logging.error(e)
            return

        if result.status_code != 200:
            logging.error("Returned %s when fetching %s" % (result.status_code, self.url))
            return

        try:
            encoding = chardet.detect(result.content)['encoding']
            s = unicode(result.content, encoding)
            s = re.compile("\r\n", re.M).sub("\n", s) # dos2unix

            # Notes:
            # SYNOPSIS, ABSTRACT, ABTRACT, and ABSTRCT are interchangable
            # Ignore case
            p = re.compile("^VENUE : (?P<venue>.+?)\n\n.*^(?P<info>(ABS?TRA?CT|SYNOPSIS).+)",
                           re.M | re.S | re.I)
            m = p.search(s)
            venue = m.group("venue").strip()
            self.venue = re.compile("\n\s+", re.M).sub("\n", venue) # trim space in each line
            self.info = m.group("info").strip()
        except:
            logging.warning("Can't retrive venue and info from %s\n%s" % (self.url, s))

        self.put()
