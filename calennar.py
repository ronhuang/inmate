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
import logging
from BeautifulSoup import BeautifulSoup, SoupStrainer


class NusCsHandler(webapp.RequestHandler):
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
        entries = SoupStrainer('tr', bgcolor="#FFFFFF")
        soup = BeautifulSoup(result.content,
                             parseOnlyThese=entries)
        for row in soup:
            try:
                dt = row.contents[0].p
                date = dt.contents[0].extract()
                time = dt.contents[1].extract()

                info = row.contents[1].p
                url = info.a['href']
                title = info.a.string.extract()
                name = info.contents[2].extract()
                institute = info.contents[3].extract()

                #print '\n'.join([date, time, url, title, name, institute])
                #break
            except Exception, e:
                logging.error("Error %s @ %s" % (e, unicode(row)))
                continue


class NusEceHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('NUS ECE')


def main():
    actions = [
        ('/calennar/nuscs.ics', NusCsHandler),
        ('/calennar/nusece.ics', NusEceHandler),
        ]
    application = webapp.WSGIApplication(actions, debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
