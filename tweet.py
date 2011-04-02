#!/usr/bin/env python
#
# Copyright (c) 2011 Ron Huang
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
import logging
from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import urlfetch
from google.appengine.api import memcache
import blackbirdpy
import tweepy
from configs import CONSUMER_KEY, CONSUMER_SECRET, CALLBACK
from utils import Cookies
from models import TweetAccessToken


class MainHandler(webapp.RequestHandler):
    def get(self):
        query = TweetAccessToken.gql("WHERE name = :name", name="the_only_one")
        token = query.get()
        if token:
            self.response.out.write('The service is available. Try <a href="/tweet/20">this</a>.')
        else:
            self.redirect("/tweet/setup")

class TweetHandler(webapp.RequestHandler):
    def get(self, tweet_id):
        # get twitter access token from datastore
        token_key = None
        token_secret = None
        query = TweetAccessToken.gql("WHERE name = :name", name="the_only_one")
        token = query.get()
        if token:
            token_key = token.clavis
            token_secret = token.arcanum
        else:
            logging.error("Twitter access token unavailable")
            self.error(500)
            return

        # get authorized api
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(token_key, token_secret)
        api = tweepy.API(auth)

        try:
            embed_html = blackbirdpy.embed_tweet_html(tweet_id, None, api)
        except tweepy.TweepError, e:
            logging.warning("Failed to retrieve embed tweet (%s) html: %s", tweet_id, e)
            self.error(404)
            return

        self.response.out.write(embed_html)


class SetupHandler(webapp.RequestHandler):
    def get(self):
        # OAuth dance
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET, CALLBACK)
        try:
            url = auth.get_authorization_url()
        except tweepy.TweepError, e:
            logging.error("Failed to get a request token: %s", e)
            self.error(500)
            return

        # store the request token for later use in the callback page.
        cookies = Cookies(self)
        cookies["juyh"] = auth.request_token.key
        cookies["jhnm"] = auth.request_token.secret

        self.redirect(url)


class CallbackHandler(webapp.RequestHandler):
    def get(self):
        oauth_token = self.request.get("oauth_token", None)
        oauth_verifier = self.request.get("oauth_verifier", None)

        if oauth_token is None:
            # Invalid request!
            logging.error("Missing required parameters")
            self.error(500)
            return

        # lookup the request token
        cookies = Cookies(self)
        token_key = None
        token_secret = None

        if "juyh" in cookies:
            token_key = cookies["juyh"]
            del cookies["juyh"]
        if "jhnm" in cookies:
            token_secret = cookies["jhnm"]
            del cookies["jhnm"]

        if token_key is None or token_secret is None or oauth_token != token_key:
            # We do not seem to have this request token, show an error.
            logging.error("Invalid token")
            self.error(500)
            return

        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_request_token(token_key, token_secret)

        # fetch the access token
        try:
            auth.get_access_token(oauth_verifier)
        except tweepy.TweepError, e:
            # Failed to get access token
            logging.error("Failed to get access token: %s", e)
            self.error(500)
            return

        # remember on server
        query = TweetAccessToken.gql("WHERE name = :name", name="the_only_one")
        token = query.get()
        if token:
            token.clavis = auth.access_token.key
            token.arcanum = auth.access_token.secret
        else:
            token = TweetAccessToken(name="the_only_one", clavis=auth.access_token.key, arcanum=auth.access_token.secret)
        token.put()

        self.redirect("/tweet")


def main():
    actions = [
        ('/tweet$', MainHandler),
        ('/tweet/([0-9]+)$', TweetHandler),
        ('/tweet/setup$', SetupHandler),
        ('/tweet/callback$', CallbackHandler),
        ]
    application = webapp.WSGIApplication(actions, debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
