import gevent.monkey
gevent.monkey.patch_all()
import gevent.pywsgi
import gevent.pool
import gevent
import sys
import argparse
import logging
import urllib
import urlparse
import webbrowser
import pprint
import json
import random
import string
import itertools


log = logging.getLogger(__name__)


FB_DATA =  string.Template("""
	{"id":"$id","name":"Ivanov$id Ivan$id","first_name":"Ivanov$id","last_name":"Ivan$id","link":"http:\/\/www.facebook.com\/ivan$id","username":"ivan$id","work":[{"employer":{"id":"1","name":"test"},"start_date":"0000-00"},{"employer":{"id":"2","name":"test1"},"start_date":"0000-00","end_date":"0000-00"}],"gender":"male","email":"ivan$id\u0040example.com","timezone":4,"locale":"en_US","verified":true,"updated_time":"2012-11-22T14:57:50+0000"}
""".strip())

def handle (env, start_response):
	if env['PATH_INFO'].startswith('/oauth/access_token'):
		body = "access_token=%s&expires=5103468" % ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(112))
		start_response('200 OK', [('Content-Type', 'text/html')])
	elif env['PATH_INFO'].startswith('/me'):
		uid = env['id_gen'].next()

		body = FB_DATA.substitute(id = uid)
		start_response('200 OK', [('Content-Type', 'text/html')])
	else:
		log.debug(pprint.pformat(env))

		body = '<h1>404 Not Found</h1>'
		start_response('404 Not Found', [('Content-Type', 'text/html')])

	# emulate latency
	gevent.sleep(0.100)

	return [body]

def auth_handle (env, start_response):
	if env['PATH_INFO'] == '/on_authed':
		q = urlparse.parse_qs(env['QUERY_STRING'])
		[code] = q['code']
		[state] = q['state']
		assert state == 'test'

		params = dict(
			client_id = env['app_id'],
			redirect_uri = 'http://localhost:6543/on_authed',
			client_secret = env['app_secret'],
			code = code,
		)
		# fb_host = 'graph.facebook.com'
		# fb_host = 'localhost:8888'
		fb_host = 'localhost'
		url = 'https://' + fb_host + '/oauth/access_token?' + urllib.urlencode(params)
		resp = urllib.urlopen(url).read()
		resp = urlparse.parse_qs(resp)
		[access_token] = resp['access_token']
		# [expires] = resp['expires']

		params = dict(
			access_token = access_token,
		)
		url = 'https://' + fb_host + '/me?' + urllib.urlencode(params)
		resp = urllib.urlopen(url).read()
		resp = json.loads(resp)
		assert 'error' not in resp
		assert 'id' in resp

		body = "<b>ok</b>"
		start_response('200 OK', [('Content-Type', 'text/html')])
	else:
		body = '<h1>404 Not Found</h1>'
		start_response('404 Not Found', [('Content-Type', 'text/html')])

	return [body]


class QuietWSGIHandler (gevent.pywsgi.WSGIHandler):
	def log_request (self, *args, **kwargs):
		"""don't spam to stderr"""

def run ():
	parser = argparse.ArgumentParser()
	parser.add_argument('--host', default = '0.0.0.0')
	parser.add_argument('--port', default = 8888, type = int)
	parser.add_argument('--pool-size', default = 10, type = int, help = "pre-spawned acceptor number")
	parser.add_argument('--backlog', default = 10, type = int, help = "listen backlog")
	parser.add_argument('--test', action = 'store_true', help = "run test using config file")
	parser.add_argument('--test-config', default = 'config.json', type = str, help = "config file for running test")
	parser.add_argument('--loglevel', default = 'DEBUG', type = str, help = "logging level")
	parser.add_argument('--worker-id', default = 1, type = int, help = "worker id (for data generation)")
	parser.add_argument('--worker-num', default = 1, type = int, help = "total worker number (for data generation)")
	args = parser.parse_args()

	logging.basicConfig(level = getattr(logging, args.loglevel))

	if args.test:
		with open(args.test_config, 'r') as f:
			env = json.load(f)
		auth_server = gevent.pywsgi.WSGIServer(('localhost', 6543), auth_handle, handler_class = QuietWSGIHandler, environ = env)
		auth_server.start()

		#https://developers.facebook.com/docs/reference/dialogs/oauth/
		#https://developers.facebook.com/docs/howtos/login/server-side-login/
		params = dict(
			client_id = env['app_id'],
			redirect_uri = 'http://localhost:6543/on_authed',
			scope = 'email',
			state = 'test',
		)
		url = 'https://www.facebook.com/dialog/oauth/?' + urllib.urlencode(params)
		webbrowser.open(url)

	log.info("Serving on %s:%s..." % (args.host, args.port))

	env = dict(
		id_gen = itertools.count(args.worker_id, args.worker_num),
	)
	server = gevent.pywsgi.WSGIServer((args.host, args.port), handle,
		spawn = gevent.pool.Pool(args.pool_size),
		handler_class = QuietWSGIHandler,
		backlog = args.backlog,
		environ = env,
	)
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		pass

if __name__ == '__main__':
	run()
