from hashlib import sha256
from urllib import quote, unquote
from urlparse import urlparse
from flask import Flask, abort, request, redirect, render_template, jsonify
from jinja2 import Template
from swiftly.client import Client

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DEBUG = False,
    USE_EVENTLET = False,
    SWIFTLY_CACHE_PATH = './.swiftly',
    USE_SNET = False,
    CF_USERNAME = '',
    CF_API_KEY = '',
    CF_REGION = 'DFW',
    CF_AUTH_URL = 'https://identity.api.rackspacecloud.com/v2.0',
    CF_CONTAINER = 'cfshorty',
    CF_CDN_URL = None
))
app.config.from_envvar('CFSHORTY_SETTINGS', silent=False)

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
If you are not redirected automatically to <a href='{{url}}'>{{url}}</a> follow <a href='{{url}}'>this link</a>
</body>
</html>
'''
redirect_template = Template(redir_template_text)

def _swiftlyv(*args):
    print args

def _shortcode(url, length=6):
    return sha256(url).hexdigest()[-length:]

def _save_url(shortcode, longurl):
    #should just have swiftly use before_request
    cf = Client(app.config['CF_AUTH_URL'], app.config['CF_USERNAME'], app.config['CF_API_KEY'],
            snet=app.config['USE_SNET'], cache_path=app.config['SWIFTLY_CACHE_PATH'],
            eventlet=app.config['USE_EVENTLET'], region=app.config['CF_REGION'],
            verbose=_swiftlyv)
    try:
        s = cf.put_object(app.config['CF_CONTAINER'], shortcode,
                          contents=redirect_template.render(url=longurl),
                          headers={'x-object-meta-longurl': longurl, 'content-type': 'text/html'})
        print s
    except Exception:
        #because we're ghetto's we'll retry when swiftly loses the connection
        try:
            print "farking retrying...damn it..."
            s = cf.put_object(app.config['CF_CONTAINER'], shortcode,
                              contents=redirect_template.render(url=longurl),
                              headers={'x-object-meta-longurl': longurl, 'content-type': 'text/html'})
            print s
        except Exception as err:
            print "Got -> %s" % err
            s = (500, None, None)
    if s[0] // 100 == 2:
        return True
    else:
        return False

def _get_url(source):
    cf = Client(app.config['CF_AUTH_URL'], app.config['CF_USERNAME'], app.config['CF_API_KEY'],
            snet=app.config['USE_SNET'], cache_path=app.config['SWIFTLY_CACHE_PATH'],
            eventlet=app.config['USE_EVENTLET'], region=app.config['CF_REGION'],
            verbose=_swiftlyv)
    res = cf.head_object(app.config['CF_CONTAINER'], source)
    if not res[0] == 200:
        return None
    else:
        return res[2].get('x-object-meta-longurl', None)

@app.route('/shorten')
def shorten():
    urlarg = request.args.get('longurl')
    if urlarg:
        clean = unquote(urlarg)
        parsed = urlparse(clean)
        if parsed.scheme and parsed.netloc:
            code  = _shortcode(clean)
            if _save_url(code, clean):
                return jsonify({'shortcode': code,
                                'shorturl': '%s/%s' % (request.host, code),
                                'cdnshort': '%s/%s' % (app.config['CF_CDN_URL'] or request.host, code),
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
        abort(400)
    url = _get_url(shortcode)
    if not url:
        abort(404)
    else:
        return redirect(url)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=app.config['DEBUG'])
