cfshorty
========

This is the ghetto URL Shortner running at [http://blk.io](http://blk.io) that was inspired by [this bit.ly engineering blog post](http://word.bitly.com/post/62914279559/z-proxy)

Its built with Flask and uses the Rackspace Cloud Files object store for...storage...of...objects. Tiny tiny objects.

It works by turning a loooong url into a short code (through magic!). The short code is then uploaded as an object to Cloud Files, and served up via the Cloud Files CDN service.  This allows you to expand url's without having to go through the blk.io web service again. 

The contents of the uploaded object is just a simple HTML page that redirects a visitor the original long url when its accessed via CDN at http://small.blk.io/<SomeShortCode>:

```python
fhines@kira:~$ http http://small.blk.io/e08e9d
HTTP/1.1 200 OK
Accept-Ranges: bytes
Cache-Control: public, max-age=259160
Connection: keep-alive
Content-Encoding: gzip
Content-Length: 274
Content-Type: text/html
Date: Mon, 07 Oct 2013 07:10:56 GMT
ETag: b592164ee9183282f9b2259d154d23cf
Expires: Thu, 10 Oct 2013 07:10:16 GMT
Last-Modified: Mon, 07 Oct 2013 06:41:14 GMT
Vary: Accept-Encoding
X-Object-Meta-Longurl: http://bloomberg.com
X-Timestamp: 1381128074.94653
X-Trans-Id: txb4163f76b17c4753bc188-0052525e7fdfw1

<!DOCTYPE HTML>
<html lang="en-US">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="1; url=http://bloomberg.com">
    <script>
        window.location.href = "http://bloomberg.com"
    </script>
    <title>http://bloomberg.com - Page Redirection</title>
</head>
<body>
If you are not redirected automatically to <a href='http://bloomberg.com'>http://bloomberg.com</a> follow <a href='http://bloomberg.com'>this link</a>
</body>
</html>
```

In addition, when the object is stored in Cloud Files a meta data key called "X-Object-Meta-Longurl" is also set pointing to the original url. This allows you to determine the long url of a shortcode stored in Cloud Files by simply performing a head on the object. This is the method used by the Flask app when expanding a url by hitting http://blk.io/<SomeShortCode>

Other handy things you could do ? Use Cloud Files expiring object support to automatically expire url's...and other stuff, and things, yea...
