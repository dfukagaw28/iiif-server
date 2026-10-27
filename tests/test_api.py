import importlib
import json

import pytest
import tornado.testing

import server
from api import hyaku2017
from api import hyaku2020


class ApiTestCase(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        return server.make_app()

    def fetch_json(self, path):
        response = self.fetch(path)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        return json.loads(response.body)

    def test_hyaku2017_manifest(self):
        base = hyaku2017.IIIF_SERVICE_URI
        for group, first in [('A', 1), ('C', 41), ('E', 81)]:
            with self.subTest(group=group):
                manifest = self.fetch_json(f'/hyaku2017{group}/manifest.json')
                self.assertEqual(manifest['@id'], f'{base}hyaku2017{group}/manifest.json')
                self.assertEqual(manifest['@type'], 'sc:Manifest')
                canvases = manifest['sequences'][0]['canvases']
                self.assertEqual(len(canvases), 20)
                self.assertEqual(canvases[0]['label'], f'card{first:03d}')
                self.assertEqual(canvases[-1]['label'], f'card{first + 19:03d}')

    def test_hyaku2017_canvas(self):
        base = hyaku2017.IIIF_SERVICE_URI
        canvas = self.fetch_json('/hyaku2017A/canvas/00002')
        self.assertEqual(canvas['@id'], f'{base}hyaku2017A/canvas/00002')
        self.assertEqual(canvas['label'], 'card001')
        service = canvas['images'][0]['resource']['service']
        self.assertEqual(service['@id'], f'{base}v2/image/hyaku2017/002.tif')

    def test_hyaku2017_canvas_matches_manifest(self):
        manifest = self.fetch_json('/hyaku2017B/manifest.json')
        for canvas in manifest['sequences'][0]['canvases']:
            path = canvas['@id'].removeprefix(hyaku2017.IIIF_SERVICE_URI)
            self.assertEqual(self.fetch_json(f'/{path}'), canvas)

    def test_hyaku2017_unknown_group(self):
        response = self.fetch('/hyaku2017F/manifest.json')
        self.assertEqual(response.code, 404)

    def test_hyaku2020_manifest(self):
        base = hyaku2020.IIIF_SERVICE_URI
        manifest = self.fetch_json('/hyaku2020/manifest.json')
        self.assertEqual(manifest['@id'], f'{base}hyaku2020/manifest.json')
        canvases = manifest['sequences'][0]['canvases']
        self.assertEqual(len(canvases), 12)
        self.assertEqual(canvases[0]['label'], '1kami 1efuda 1')
        self.assertEqual(canvases[-1]['label'], '2shimo 2jifuda 4')

    def test_hyaku2020_canvas(self):
        base = hyaku2020.IIIF_SERVICE_URI
        canvas = self.fetch_json('/hyaku2020/canvas/2shimo/2jifuda/3')
        self.assertEqual(canvas['@id'], f'{base}hyaku2020/canvas/2shimo/2jifuda/3')
        service = canvas['images'][0]['resource']['service']
        self.assertEqual(service['@id'], f'{base}v2/image/2shimo_2jifuda_3.tif')

    def test_hyaku2020_canvas_matches_manifest(self):
        manifest = self.fetch_json('/hyaku2020/manifest.json')
        for canvas in manifest['sequences'][0]['canvases']:
            path = canvas['@id'].removeprefix(hyaku2020.IIIF_SERVICE_URI)
            self.assertEqual(self.fetch_json(f'/{path}'), canvas)

    def test_ld_json_content_type(self):
        response = self.fetch('/hyaku2020/manifest.json', headers={'Accept': '*/*'})
        self.assertEqual(response.headers['Content-Type'], 'application/ld+json')


@pytest.mark.parametrize('module', [hyaku2017, hyaku2020])
def test_base_url(monkeypatch, module):
    monkeypatch.setenv('BASE_URL', 'https://test.example/')
    try:
        importlib.reload(module)
        assert module.IIIF_SERVICE_URI == 'https://test.example/'
    finally:
        monkeypatch.delenv('BASE_URL')
        importlib.reload(module)
    assert module.IIIF_SERVICE_URI == 'https://iiif.tiramis2.doshisha.ac.jp/'
