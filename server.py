import json
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


def handle_fetch_error(request, e):
    logging.debug(e)
    if isinstance(e, tornado.httpclient.HTTPError) and e.response is not None:
        request.set_status(e.response.code, e.response.reason)
        logging.debug(e.response.body)
    else:
        # No response from the image server (connection error, timeout, etc.)
        logging.error(f'Failed to fetch from iipsrv: {e!r}')
        request.set_status(502)


IIIF_IMAGE_2_CONTEXT = 'http://iiif.io/api/image/2/context.json'
IIIF_IMAGE_2_LEVEL2 = 'http://iiif.io/api/image/2/level2.json'

## Features defined in Image API 2.1 (v3 adds e.g. sizeUpscaling, which v2 lacks)
IIIF_IMAGE_2_FEATURES = {
    'baseUriRedirect', 'canonicalLinkHeader', 'cors', 'jsonldMediaType',
    'mirroring', 'profileLinkHeader', 'regionByPct', 'regionByPx',
    'regionSquare', 'rotationArbitrary', 'rotationBy90s', 'sizeAboveFull',
    'sizeByConfinedWh', 'sizeByDistortedWh', 'sizeByForcedWh', 'sizeByH',
    'sizeByPct', 'sizeByW', 'sizeByWh', 'sizeByWhListed',
}


## Convert an Image API 3 info.json (iipsrv runs with IIIF_VERSION=3)
## into an Image API 2.1 one, for clients that only read v2 (e.g. old OpenSeadragon)
def info_v3_to_v2(info, image_id):
    profile = {}
    if 'extraFormats' in info:
        profile['formats'] = info['extraFormats']
    if 'extraQualities' in info:
        profile['qualities'] = info['extraQualities']
    if 'extraFeatures' in info:
        profile['supports'] = [f for f in info['extraFeatures'] if f in IIIF_IMAGE_2_FEATURES]
    for key in ('maxWidth', 'maxHeight', 'maxArea'):
        if key in info:
            profile[key] = info[key]

    data = {
        '@context': IIIF_IMAGE_2_CONTEXT,
        '@id': image_id,
        'protocol': 'http://iiif.io/api/image',
        'width': info['width'],
        'height': info['height'],
    }
    for key in ('sizes', 'tiles', 'service'):
        if key in info:
            data[key] = info[key]
    data['profile'] = [IIIF_IMAGE_2_LEVEL2, profile] if profile else [IIIF_IMAGE_2_LEVEL2]
    return data


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

    async def get(self, version, query):
        identifier_raw = resolve_identifier(query)
        identifier_quoted = quote(identifier_raw, safe='')

        try:
            response = await fetch_iipsrv(f'{ identifier_quoted }/info.json')
        except (tornado.httpclient.HTTPError, OSError) as e:
            handle_fetch_error(self, e)
        else:
            # Get the response body from the image server
            data = response.buffer.read()

            if version == 'v2':
                # The id is the URL requested by the client
                image_id = f'{ BASE_URL }v2/image/{ quote(query, safe="/") }'
                data = json.dumps(info_v3_to_v2(json.loads(data), image_id), indent=2)
                self.set_header('Content-Type', f'application/ld+json;profile="{ IIIF_IMAGE_2_CONTEXT }"')
            else:
                # Rewrite id
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
        # Keep only the characters used in IIIF parameters (e.g. "pct:", "^!w,h")
        # so that "&", "#", etc. cannot inject extra parameters into the iipsrv query
        params_quoted = quote(params, safe='/,:!^')

        try:
            response = await fetch_iipsrv(f'{ identifier_quoted }/{ params_quoted }')
        except (tornado.httpclient.HTTPError, OSError) as e:
            handle_fetch_error(self, e)
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
        (r"/(v[23])/image/(.+)/info\.json", ImageInfoHandler),
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
