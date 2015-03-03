#! /usr/bin/env python
import API
import argparse
from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server

DEFAULT_PORT = 8080
DEFAULT_DBNAME = "wn_bacon"

def get_doc():
    # with open('api_doc.txt') as fp:
    with open('API.html') as fp:
        return [line for line in fp]

def application(environ, start_response):
    setup_testing_defaults(environ)
    api.set_environ(environ)

    status = '200 OK'
    headers = [('Content-type', 'text/plain')]

    try:
        if api._get_page() == 'doc':
            content = get_doc()
            headers = [('Content-type', 'text/html')]
        else:
            content = api._application()
            headers = [('Content-type', 'application/json'), ('Access-Control-Allow-Origin', '*')]
    except AttributeError:
        status = '204 No Content'
        content = []

    start_response(status, headers)
    return content

parser = argparse.ArgumentParser(description='Bigram Server', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT)
parser.add_argument('--dbname', '-d', default=DEFAULT_DBNAME)
parser.add_argument('--read_gpickle', '-rgp', action='store_true', help='gpickle')
args = parser.parse_args()

api = API.API(args.dbname, read_gpickle=args.read_gpickle)
httpd = make_server('', args.port, application)
print "Serving %s on port %d..." % (args.dbname, args.port)
httpd.serve_forever()
