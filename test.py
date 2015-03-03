from mod_python import apache, util
import json

def index(req):
    req.content_type = 'application/json'
    args = util.parse_qs(req.args)
    out = {}

    if args['method'][0] == "add":
        out['result'] = int(args['x'][0]) + int(args['y'][0])
    else:
        out['error'] = 500
        out['error_str'] = "Method unknown."

    req.write(json.dumps(out))


