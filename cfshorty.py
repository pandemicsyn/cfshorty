from hashlib import sha256
from urllib import unquote
from urlparse import urlparse
from flask import Flask, abort, request, redirect, render_template, jsonify, \
    send_from_directory
from werkzeug.contrib.cache import MemcachedCache
from jinja2 import Template
from swiftly.client import StandardClient
import sys

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DEBUG=False,
    USE_EVENTLET=False,
    SWIFTLY_AUTH_CACHE_PATH='./.swiftly',
    USE_SNET=False,
    CF_USERNAME='',
    CF_API_KEY='',
    CF_REGION='DFW',
    CF_AUTH_URL='https://identity.api.rackspacecloud.com/v2.0',
    CF_CONTAINER='cfshorty',
    CF_CDN_URL=None,
    GOOGLE_ANALYTICS_CODE=None,
    USE_MEMCACHE=False,
    MEMCACHE_HOSTS=['127.0.0.1:11211'],
    CACHE_TTL=604800,
))
app.config.from_envvar('CFSHORTY_SETTINGS', silent=False)

if app.config['USE_MEMCACHE']:
    from werkzeug.contrib.cache import MemcachedCache
    cache = MemcachedCache(app.config['MEMCACHE_HOSTS'],
                           default_timeout=app.config['CACHE_TTL'],
                           key_prefix='cfshorty:')
else:
    cache = lambda *s: None
    cache.get = cache.set = lambda *s: None

redir_template_text = '''
<!DOCTYPE HTML>
<html lang="en-US">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="1; url={{url}}">
    <script>
        window.location.href = "{{url}}"
    </script>
    <title>{{url}} - Page Redirection</title>
</head>
<body>
If you are not redirected automatically to <a href='{{url}}'>{{url}}</a>
 follow <a href='{{url}}'>this link</a>
</body>
</html>
'''
redirect_template = Template(redir_template_text)


def _swiftlyv(*args):
    """Little swiftly verbose wrapper"""
    if app.config['DEBUG'] is True:
        print args


def gen_shortcode(url, length=6):
    """Generate the shortcode for a url

    :param url: url to shorten
    :param length: length of the returned shortcode
    :returns: string shortcode of url
    """
    return sha256(url).hexdigest()[-length:]


def _save_url(shortcode, longurl):
    """Save url to Swift"""
    # should just have swiftly use before_request
    try:
        s = cf.put_object(app.config['CF_CONTAINER'], shortcode,
                          contents=redirect_template.render(url=longurl),
                          headers={'x-object-meta-longurl': longurl,
                                   'content-type': 'text/html'}
                          )
        if app.config['DEBUG'] is True:
            print s
    except Exception:
        try:
            print "farking retrying...damn it..."
            s = cf.put_object(app.config['CF_CONTAINER'], shortcode,
                              contents=redirect_template.render(url=longurl),
                              headers={'x-object-meta-longurl': longurl,
                                       'content-type': 'text/html'}
                              )
            if app.config['DEBUG'] is True:
                print s
        except Exception as err:
            print "Got -> %s" % err
            s = (500, None, None)
    if s[0] // 100 == 2:
        cache.set(shortcode, longurl, app.config['CACHE_TTL'])
        return True
    else:
        return False


def _get_url(shortcode):
    """Retrive url from cache or swift"""
    longurl = cache.get(shortcode)
    if longurl:
        return longurl
    else:
        cf = StandardClient(
            auth_url=app.config['CF_AUTH_URL'],
            auth_user=app.config['CF_USERNAME'],
            auth_key=app.config['CF_API_KEY'],
            snet=app.config['USE_SNET'],
            auth_cache_path=app.config['SWIFTLY_AUTH_CACHE_PATH'],
            eventlet=app.config['USE_EVENTLET'],
            region=app.config['CF_REGION'],
            verbose=_swiftlyv
        )
        res = cf.head_object(app.config['CF_CONTAINER'], shortcode)
        if not res[0] == 200:
            return None
        else:
            longurl = res[2].get('x-object-meta-longurl', None)
            cache.set(shortcode, longurl)
            return longurl


@app.route('/shorten')
def shorten():
    urlarg = request.args.get('longurl')
    if urlarg:
        clean = unquote(urlarg)
        parsed = urlparse(clean)
        if parsed.scheme and parsed.netloc:
            code = gen_shortcode(clean)
            if _save_url(code, clean):
                return jsonify({'shortcode': code,
                                'shorturl': '%s/%s' % (request.host, code),
                                'cdnshort': '%s/%s' % (app.config['CF_CDN_URL']
                                                       or request.host, code),
                                'longurl': clean})
            else:
                abort(500)
        else:
            abort(400)
    else:
        abort(400)


@app.route('/<shortcode>')
def resolvecode(shortcode):
    if len(shortcode) != 6:
        abort(404)
    url = _get_url(shortcode)
    if not url:
        abort(404)
    else:
        return redirect(url)


@app.route('/robots.txt')
def domoarigato():
    return send_from_directory(app.static_folder, request.path[1:])


@app.route('/')
def index():
    return render_template('index.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error=404), 404

if __name__ == '__main__':
    try:
        cf = StandardClient(
            auth_url=app.config['CF_AUTH_URL'],
            auth_user=app.config['CF_USERNAME'],
            auth_key=app.config['CF_API_KEY'],
            snet=app.config['USE_SNET'],
            auth_cache_path=app.config['SWIFTLY_AUTH_CACHE_PATH'],
            eventlet=app.config['USE_EVENTLET'],
            region=app.config['CF_REGION'],
            verbose=_swiftlyv
        )
        # Create the container if it doesn't exist
        if cf.head_container(app.config['CF_CONTAINER'])[0] != 204:
            cf.put_container(app.config['CF_CONTAINER'])
    except Exception as err:
        print "Got -> %s" % err
        sys.exit(1)
    app.run(host='0.0.0.0', debug=app.config['DEBUG'])
