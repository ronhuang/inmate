(function() {

  // Localize jQuery variable
  var jQuery;

  /******** Load jQuery if not present *********/
  if (window.jQuery === undefined || window.jQuery.fn.jquery !== '1.4.2') {
    var script_tag = document.createElement('script');
    script_tag.setAttribute("type", "text/javascript");
    script_tag.setAttribute("src", "http://ajax.googleapis.com/ajax/libs/jquery/1.4.2/jquery.min.js");
    script_tag.onload = scriptLoadHandler;
    script_tag.onreadystatechange = function () { // Same thing but for IE
      if (this.readyState == 'complete' || this.readyState == 'loaded') {
        scriptLoadHandler();
      }
    };
    // Try to find the head, otherwise default to the documentElement
    (document.getElementsByTagName("head")[0] || document.documentElement).appendChild(script_tag);
  } else {
    // The jQuery version on the window is the one we want to use
    jQuery = window.jQuery;
    main();
  }

  /******** Called once jQuery has loaded ******/
  function scriptLoadHandler() {
    // Restore $ and window.jQuery to their previous values and store the
    // new jQuery in our local jQuery variable
    jQuery = window.jQuery.noConflict(true);
    // Call our main function
    main();
  };

  /******** Our main function ********/
  function main() {
    jQuery(document).ready(function($) {
      /******* Load CSS *******/
      var css_link = $("<link>", {
        rel: "stylesheet",
        type: "text/css",
        href: "style.css"
      });
      css_link.appendTo('head');

      /******* Load HTML *******/
      $.getJSON("http://{{server}}/tweet/json/{{tweet_id}}?callback=?", buildEmbedTweet);
    });
  };

  function tweetLink(text, href) {
    return '<a href="' + href + '" rel="nofollow">' + text + '</a>';
  }

  function parseText(text) {
    return text.replace('\n', ' ')
      .replace(/[A-Za-z]+:\/\/[A-Za-z0-9-_]+\.[A-Za-z0-9-_:%&\?\/.=]+/g, function(url) {
        return tweetLink(url, url);
	  })
      .replace(/[@]+[A-Za-z0-9-_]+/g, function(u) {
	    var username = u.replace("@","")
        return tweetLink(u, 'http://twitter.com/' + username);
	  })
      .replace(/[#]+[A-Za-z0-9-_]+/g, function(t) {
	    var tag = t.replace("#","%23")
        return tweetLink(t, 'http://twitter.com/search?q=' + tag);
	  });
  };

  // adapted from http://widgets.twimg.com/j/1/widget.js
  function prettyDate(a) {
    var b = new Date();
    var c = new Date(a);
    if (navigator.userAgent.match(/MSIE\s([^;]*)/)) {
      c = Date.parse(a.replace(/( \+)/, ' UTC$1'));
    }
    var d = b - c;
    var e = 1000;
    var minute = e * 60;
    var hour = minute * 60
    var day = hour * 24;
    var week = day * 7;

    if (isNaN(d) || d < 0) {
      return ""
    }
    if (d < e * 7) {
      return "right now"
    }
    if (d < minute) {
      return Math.floor(d / e) + " seconds ago"
    }
    if (d < minute * 2) {
      return "about 1 minute ago"
    }
    if (d < hour) {
      return Math.floor(d / minute) + " minutes ago"
    }
    if (d < hour * 2) {
      return "about 1 hour ago"
    }
    if (d < day) {
      return Math.floor(d / hour) + " hours ago"
    }

    var v = a.split(' ');
    return c.getDate() + " " + v[1];
  };

  function localDate(str) {
    var v=str.split(' ');
    return new Date(Date.parse(v[1]+" "+v[2]+", "+v[5]+" "+v[3]+" UTC"));
  };

  function buildEmbedTweet(data) {
    // Format some data
    var tweet_url = 'http://twitter.com/' + data['user']['screen_name'] + '/status/' + data['id'];
    var local_ts = localDate(data['created_at']);
    var pretty_ts = prettyDate(data['created_at']);
    var profile_url = 'http://twitter.com/' + data['user']['screen_name'];

    // build box
    var box = $('<div></div>').addClass('bbpBox' + {{tweet_id}});
    var tweet = $('<p></p>').addClass('bbpTweet');
    box.append(tweet);

    var text = parseText(data.text);
    tweet.append(text);

    var ts = $('<span></span>').addClass('timestamp');
    ts.append($('<a></a>').attr('title', local_ts).attr('href', tweet_url).text(pretty_ts));
    ts.append(' via ');
    ts.append(data['source']);
    tweet.append(ts);

    var md = $('<span></span>').addClass('metadata');
    tweet.append(md);

    var au = $('<span></span>').addClass('author');
    md.append(au);

    var pf = $('<a></a>').attr('href', profile_url).html('<img src="' + data['user']['profile_image_url'] + '">');
    au.append(pf);

    au.append($('<a></a>').addClass('id').attr('href', profile_url).text('@' + data['user']['screen_name']));
    au.append($('<br/>'));
    au.append($('<span></span>').addClass('name').text(data['user']['name']));

    // find script and insert the embed tweet
    $('script[src="http://{{server}}/tweet/{{tweet_id}}"]').after(box);
  };

})(); // We call our anonymous function immediately
