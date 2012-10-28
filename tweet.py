#!/usr/bin/env python
#
# Copyright (c) 2012 Ron Huang
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


import os
from google.appengine.ext import webapp
import logging
from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import urlfetch
from google.appengine.api import memcache
import tweepy
from tweepy.parsers import RawParser
from configs import CONSUMER_KEY, CONSUMER_SECRET, CALLBACK
import utils
from models import TweetAccessToken
from validate_jsonp import is_valid_javascript_identifier
import jinja2


class MainHandler(webapp.RequestHandler):
    def get(self):
        query = TweetAccessToken.gql("WHERE name = :name", name="the_only_one")
        token = query.get()
        if token:
            self.response.out.write('The service is available. Try <a href="/tweet/20">this</a>.')
        else:
            self.redirect("/tweet/setup")


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class TweetHandler(webapp.RequestHandler):
    def get(self, tweet_id):
        # return the javascript code
        msg = {'tweet_id': tweet_id, 'server': 'inmate.ronhuang.org'}
        if utils.devel():
            msg['server'] = 'localhost:8080'

        template = jinja_environment.get_template('view/tweet.js')
        self.response.headers['Content-Type'] = "text/javascript"
        self.response.out.write(template.render(msg))


class JsonHandler(webapp.RequestHandler):
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
        api = tweepy.API(auth_handler=auth, parser=RawParser())

        json_data = api.get_status(tweet_id)

        callback = self.request.get('callback', None)
        if callback and is_valid_javascript_identifier(callback):
            self.response.headers['Content-Type'] = 'application/javascript'
            self.response.out.write("%s(%s)" % (callback, json_data))
        elif callback:
            logging.warning("Invalid callback: %s", callback)
            self.error(500)
            return
        else:
            self.response.headers['Content-Type'] = 'application/json'
            self.response.out.write(json_data)


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
        self.response.set_cookie("juyh", auth.request_token.key)
        self.response.set_cookie("jhnm", auth.request_token.secret)

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
        cookies = self.request.cookies
        token_key = None
        token_secret = None

        if "juyh" in cookies:
            token_key = cookies.get("juyh")
            self.response.delete_cookie("juyh")
        if "jhnm" in cookies:
            token_secret = cookies.get("jhnm")
            self.response.delete_cookie("jhnm")

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


app = webapp.WSGIApplication([
        ('/tweet$', MainHandler),
        ('/tweet/([0-9]+)$', TweetHandler),
        ('/tweet/json/([0-9]+)$', JsonHandler),
        ('/tweet/setup$', SetupHandler),
        ('/tweet/callback$', CallbackHandler),
        ], debug=True)
