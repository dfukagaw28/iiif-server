import logging
import os
import re
import tornado.httpclient
import tornado.ioloop
import tornado.options
import tornado.web
from urllib.parse import quote

# For custom API
from api import hyaku2017
from api import hyaku2020


BASE_URL = os.getenv('BASE_URL', 'https://iiif.example.com/')
INTERNAL_IIPSRV_BASE_URL = 'http://iipsrv/?IIIF='


async def fetch_iipsrv(query):
    http_client = tornado.httpclient.AsyncHTTPClient()
    response = await http_client.fetch(f'{ INTERNAL_IIPSRV_BASE_URL }{ query }')
    return response


def resolve_identifier(identifier):
    m = re.match(r'[0-9A-Fa-f]{64}', identifier)
    if m:
        h = m.group(0)
        return f'{h[0]}/{h[1]}/{h}.tif'
    return identifier


def set_headers(request, response):
    for key in ('Content-Type',):
        if key in response.headers:
            request.set_header(key, response.headers[key])


def write_buffers_by_chunks(request, buffer):
    while True:
        chunk = buffer.read(2048)
        if len(chunk) == 0:
            break
        request.write(chunk)


class HelloHandler(tornado.web.RequestHandler):
   def get(self):
       self.write("Hello, world")


## Image Information Request
## GET /{identifier}/info.json
class ImageInfoHandler(tornado.web.RequestHandler):
    INTERNAL_BASE_URL_BYTES = INTERNAL_IIPSRV_BASE_URL.encode('utf-8')
    EXTERNAL_BASE_URL_BYTES = BASE_URL.encode('utf-8') + b'v3/image/'

    async def get(self, query):
        identifier_raw = resolve_identifier(query)
        identifier_quoted = quote(identifier_raw, safe='')

        try:
            response = await fetch_iipsrv(f'{ identifier_quoted }/info.json')
        except tornado.httpclient.HTTPError as e:
            logging.debug(e)
            self.set_status(e.response.code, e.response.reason)
            logging.debug(e.response.body)
        else:
            # Get the response body from the image server
            data = response.buffer.read()

            # Rewrite @id
            data = data.replace(self.INTERNAL_BASE_URL_BYTES, self.EXTERNAL_BASE_URL_BYTES)

            # Set headers
            set_headers(self, response)

            # Output the response body
            self.write(data)


## Image Request
## GET /{identifier}/{region}/{size}/{rotation}/{quality}.{format}
class ImageHandler(tornado.web.RequestHandler):
    async def get(self, query, params, region, size, rotation, quality, format):
        identifier_raw = resolve_identifier(query)
        identifier_quoted = quote(identifier_raw, safe='')

        try:
            response = await fetch_iipsrv(f'{ identifier_quoted }/{ params }')
        except tornado.httpclient.HTTPError as e:
            logging.debug(e)
            self.set_status(e.response.code, e.response.reason)
            logging.debug(e.response.body)
        else:
            set_headers(self, response)
            write_buffers_by_chunks(self, response.buffer)


## Image Other Request (Redirect)
## GET /{identifier}
class ImageOtherHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        if self.request.uri[-1] == '/':
            uri = self.request.uri + 'info.json'
        else:
            uri = self.request.uri + '/info.json'
        self.redirect(uri)


def make_app():
    return tornado.web.Application([
        (r"/hello", HelloHandler),
        (r"/v[23]/image/(.+)/info\.json", ImageInfoHandler),
        (r"/v[23]/image/(.+)/(([^/]+)/([^/]+)/([^/]+)/(\w+)\.(\w+))", ImageHandler),
        (r"/v[23]/image/(.+)", ImageOtherHandler),
        hyaku2017.manifest_handler,
        hyaku2017.canvas_handler,
        hyaku2020.manifest_handler,
        hyaku2020.canvas_handler,
    ])


if __name__ == "__main__":
    tornado.options.parse_command_line()
    app = make_app()
    app.listen(80)
    tornado.ioloop.IOLoop.current().start()
