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
      $.getJSON("http://{{server}}/tweet/json/{{tweet_id}}?callback=?", buildEmbedTweet);
    });
  };

  function parseText(text) {
    return text.replace(/\n/g, ' ')
      .replace(/([A-Za-z]+:\/\/[A-Za-z0-9-_]+\.[A-Za-z0-9-_:%&\?\/.=]+)/g, '<a href="$1" target="_blank" rel="nofollow">$1</a>')
      .replace(/(^|\s)@(\w+)/g, '$1<a href="http://twitter.com/$2" target="_blank" rel="nofollow">@$2</a>')
      .replace(/(\()@(\w+)(,| |\))/g, '$1<a href="http://twitter.com/$2" target="_blank" rel="nofollow">@$2</a>$3')
      .replace(/(^|\s)#(\w+)/g, '$1<a href="http://twitter.com/search?q=%23$2" target="_blank" rel="nofollow">#$2</a>')
      .replace(/(\()#(\w+)(,| |\))/g, '$1<a href="http://twitter.com/search?q=%23$2" target="_blank" rel="nofollow">#$2</a>$3');
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
    if (d < day * 365) {
      var v = a.split(' ');
      return c.getDate() + " " + v[1];
    }
    var v = a.split(' ');
    return c.getDate() + ' ' + v[1] + ' ' + c.getFullYear().toString().slice(2);
  };

  function localDate(str) {
    var v=str.split(' ');
    return new Date(Date.parse(v[1]+" "+v[2]+", "+v[5]+" "+v[3]+" UTC"));
  };

  function buildEmbedTweet(data) {
    // Format some data
    var user  = data['user'];
    var tweet_url = 'http://twitter.com/' + user['screen_name'] + '/status/' + data['id'];
    var local_ts = localDate(data['created_at']);
    var pretty_ts = prettyDate(data['created_at']);
    var profile_url = 'http://twitter.com/' + user['screen_name'];

    // build box
    var box = $('<div></div>').addClass('bbpBox' + data['id_str']);
    box.css('background-image', 'url(' + user['profile_background_image_url'] + ')');
    box.css('background-color', '#' + user['profile_background_color']);
    box.css('padding', '20px');

    var tweet = $('<p></p>').addClass('bbpTweet');
    tweet.css('background-color', '#FAFAFA');
    tweet.css('padding', '10px 12px 10px 12px');
    tweet.css('margin', '0');
    tweet.css('min-height', '48px');
    tweet.css('color', '#' + user['profile_text_color']);
    tweet.css('font-size', '18px !important');
    tweet.css('-moz-border-radius', '5px');
    tweet.css('-webkit-border-radius', '5px');
    tweet.css('line-height', '22px');
    tweet.css('margin-bottom', '0px');
    tweet.css('text-align', 'left');
    box.append(tweet);

    var text = parseText(data.text);
    tweet.append(text);

    var ts = $('<span></span>').addClass('timestamp');
    ts.css('font-size', '12px');
    ts.css('display', 'block');
    ts.css('font-family', "'Helvetica Neue', Helvetica, Arial, sans-serif");
    ts.append($('<a></a>').attr('title', local_ts).attr('target', '_blank').attr('href', tweet_url).text(pretty_ts));
    ts.append(' via ');
    ts.append(data['source']);
    tweet.append(ts);

    var md = $('<span></span>').addClass('metadata');
    md.css('display', 'block');
    md.css('width', '100%');
    md.css('margin-top', '8px');
    md.css('padding-top', '12px');
    md.css('height', '40px');
    md.css('border-top', '1px solid #e6e6e6');
    md.css('font-family', "'Helvetica Neue', Helvetica, Arial, sans-serif");
    md.css('line-height', '19px');
    tweet.append(md);

    var au = $('<span></span>').addClass('author');
    md.append(au);

    var pf = $('<a></a>').attr('href', profile_url).attr('target', '_blank')
      .html('<img src="' + user['profile_image_url'] + '" style="float: left; margin: 0 7px 0 0; width: 38px; height: 38px"/>');
    au.append(pf);

    au.append($('<a></a>').addClass('id').attr('href', profile_url).attr('target', '_blank').css('font-weight', 'bold').text('@' + user['screen_name']));
    au.append($('<br/>'));
    au.append($('<span></span>').addClass('name').css('font-size', '12px').css('color', '#999').text(user['name']));

    // find script and insert the embed tweet
    $('script[src="http://{{server}}/tweet/{{tweet_id}}"]').after(box);

    // additional style
    tweet.find('a').css('border-bottom', '0px')
      .css('font-weight', 'normal')
      .css('color', '#' + user['profile_link_color']);
    tweet.find('a').hover(
      function() {$(this).css('text-decoration', 'underline');},
      function() {$(this).css('text-decoration', 'none');});
  };

})(); // We call our anonymous function immediately
