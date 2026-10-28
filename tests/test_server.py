import json
from unittest import mock

import tornado.httpserver
import tornado.testing
import tornado.web

import server


## Image API 3 info.json, as returned by iipsrv with IIIF_VERSION=3
INFO_JSON = b'''{
  "@context" : "http://iiif.io/api/image/3/context.json",
  "protocol" : "http://iiif.io/api/image",
  "width" : 8049,
  "height" : 6033,
  "sizes" : [ { "width" : 251, "height" : 188 } ],
  "tiles" : [ { "width" : 256, "height" : 256, "scaleFactors" : [ 1, 2, 4 ] } ],
  "id" : "http://iipsrv/?IIIF=x.tif",
  "type": "ImageService3",
  "profile" : "level2",
  "maxWidth" : 3000,
  "maxHeight" : 3000,
  "extraQualities": ["color","gray","bitonal"],
  "extraFormats": ["webp"],
  "extraFeatures": ["regionByPct","sizeUpscaling","rotationBy90s","mirroring"],
  "service": [ { "profile": "http://iiif.io/api/annex/services/physdim", "physicalScale": 0.00166667, "physicalUnits": "in" } ]
}'''


## Fake iipsrv that records the queries it receives
class FakeIipsrvHandler(tornado.web.RequestHandler):
    def initialize(self, received):
        self.received = received

    def get(self):
        self.received.append(self.request.uri)
        query = self.get_query_argument('IIIF', '')
        if query.startswith('missing.tif'):
            self.set_status(404)
            self.write('missing.tif is neither a file nor part of an image sequence')
        elif query.endswith('/info.json'):
            self.set_header('Content-Type', 'application/ld+json')
            self.write(INFO_JSON)
        else:
            self.set_header('Content-Type', 'image/jpeg')
            self.write(b'JPEG' * 1000)


class ServerTestCase(tornado.testing.AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        self.received = []
        sock, port = tornado.testing.bind_unused_port()
        self.iipsrv = tornado.httpserver.HTTPServer(tornado.web.Application([
            (r'/', FakeIipsrvHandler, {'received': self.received}),
        ]))
        self.iipsrv.add_sockets([sock])
        patcher = mock.patch.object(
            server, 'INTERNAL_IIPSRV_BASE_URL', f'http://127.0.0.1:{port}/?IIIF=')
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.iipsrv.stop()
        super().tearDown()

    def get_app(self):
        return server.make_app()

    def test_hello(self):
        response = self.fetch('/hello')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b'Hello, world')

    def test_info_json(self):
        response = self.fetch('/v3/image/x.tif/info.json')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/ld+json')
        self.assertEqual(self.received, ['/?IIIF=x.tif/info.json'])
        # The internal iipsrv URL is rewritten to the public one
        info = json.loads(response.body)
        self.assertEqual(info['id'], f'{server.BASE_URL}v3/image/x.tif')

    def test_info_json_v2(self):
        response = self.fetch('/v2/image/x.tif/info.json')
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers['Content-Type'],
            'application/ld+json;profile="http://iiif.io/api/image/2/context.json"')
        self.assertEqual(self.received, ['/?IIIF=x.tif/info.json'])
        info = json.loads(response.body)
        self.assertEqual(info['@context'], 'http://iiif.io/api/image/2/context.json')
        self.assertEqual(info['@id'], f'{server.BASE_URL}v2/image/x.tif')
        self.assertNotIn('id', info)
        self.assertEqual((info['width'], info['height']), (8049, 6033))
        self.assertEqual(info['tiles'][0]['scaleFactors'], [1, 2, 4])
        self.assertEqual(info['sizes'], [{'width': 251, 'height': 188}])
        self.assertEqual(info['service'][0]['physicalUnits'], 'in')
        self.assertEqual(info['profile'], [
            'http://iiif.io/api/image/2/level2.json',
            {
                'formats': ['webp'],
                'qualities': ['color', 'gray', 'bitonal'],
                # sizeUpscaling is not defined in Image API 2
                'supports': ['regionByPct', 'rotationBy90s', 'mirroring'],
                'maxWidth': 3000,
                'maxHeight': 3000,
            },
        ])

    def test_info_json_v2_hashed_identifier(self):
        # The @id keeps the identifier as requested, not the resolved file path
        h = 'ab' + '0' * 62
        response = self.fetch(f'/v2/image/{h}/info.json')
        self.assertEqual(response.code, 200)
        self.assertEqual(self.received, [f'/?IIIF=a%2Fb%2F{h}.tif/info.json'])
        self.assertEqual(json.loads(response.body)['@id'], f'{server.BASE_URL}v2/image/{h}')

    def test_image(self):
        response = self.fetch('/v3/image/x.tif/full/max/0/default.jpg')
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-Type'], 'image/jpeg')
        self.assertEqual(response.body, b'JPEG' * 1000)
        self.assertEqual(self.received, ['/?IIIF=x.tif/full/max/0/default.jpg'])

    def test_image_v2(self):
        response = self.fetch('/v2/image/x.tif/full/full/0/default.jpg')
        self.assertEqual(response.code, 200)
        self.assertEqual(self.received, ['/?IIIF=x.tif/full/full/0/default.jpg'])

    def test_image_params_are_passed_unchanged(self):
        for params in [
            'pct:10,10,50,50/!100,100/!90/default.jpg',
            'square/^max/0/gray.png',
            '0,0,100,100/^pct:50/180/bitonal.webp',
        ]:
            with self.subTest(params=params):
                self.received.clear()
                response = self.fetch(f'/v3/image/x.tif/{params}')
                self.assertEqual(response.code, 200)
                self.assertEqual(self.received, [f'/?IIIF=x.tif/{params}'])

    def test_image_params_cannot_inject_iipsrv_parameters(self):
        response = self.fetch(
            '/v3/image/x.tif/full/max/0%26FIF=..%2Fother.tif%26CVT=png/default.jpg')
        self.assertEqual(response.code, 200)
        self.assertEqual(
            self.received,
            ['/?IIIF=x.tif/full/max/0%26FIF%3D../other.tif%26CVT%3Dpng/default.jpg'])

    def test_identifier_is_escaped(self):
        response = self.fetch('/v3/image/..%2Fsecret%26CVT=png.tif/info.json')
        self.assertEqual(response.code, 200)
        self.assertEqual(self.received, ['/?IIIF=..%2Fsecret%26CVT%3Dpng.tif/info.json'])

    def test_hashed_identifier(self):
        h = 'ab' + '0' * 62
        response = self.fetch(f'/v3/image/{h}/info.json')
        self.assertEqual(response.code, 200)
        self.assertEqual(self.received, [f'/?IIIF=a%2Fb%2F{h}.tif/info.json'])

    def test_redirect_to_info_json(self):
        for path in ['/v3/image/x.tif', '/v3/image/x.tif/']:
            with self.subTest(path=path):
                response = self.fetch(path, follow_redirects=False)
                self.assertEqual(response.code, 302)
                self.assertEqual(response.headers['Location'], '/v3/image/x.tif/info.json')

    def test_not_found_is_passed_through(self):
        for path in [
            '/v3/image/missing.tif/info.json',
            '/v2/image/missing.tif/info.json',
            '/v3/image/missing.tif/full/max/0/default.jpg',
        ]:
            with self.subTest(path=path):
                response = self.fetch(path)
                self.assertEqual(response.code, 404)
                # The error message from iipsrv (with internal paths) is not exposed
                self.assertNotIn(b'neither a file', response.body)


class UnreachableIipsrvTestCase(tornado.testing.AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()
        # Reserve a port and close it so that nothing is listening on it
        sock, port = tornado.testing.bind_unused_port()
        sock.close()
        patcher = mock.patch.object(
            server, 'INTERNAL_IIPSRV_BASE_URL', f'http://127.0.0.1:{port}/?IIIF=')
        patcher.start()
        self.addCleanup(patcher.stop)

    def get_app(self):
        return server.make_app()

    def test_bad_gateway(self):
        for path in [
            '/v3/image/x.tif/info.json',
            '/v3/image/x.tif/full/max/0/default.jpg',
        ]:
            with self.subTest(path=path):
                response = self.fetch(path)
                self.assertEqual(response.code, 502)
