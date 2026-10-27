import json
import os
import tornado.web

IIIF_IMAGE_CONTEXT = 'http://iiif.io/api/image/2/context.json'
IIIF_PRESENTATION_CONTEXT = 'http://iiif.io/api/presentation/2/context.json'
IIIF_IMAGE_API_2 = 'http://iiif.io/api/image/2/level2.json'
IIIF_SERVICE_URI = os.getenv('BASE_URL', 'https://iiif.tiramis2.doshisha.ac.jp/')
HEIGHT = 4960
WIDTH = 3504


##
def get_collection_name():
    return 'hyaku2020'


##
def get_image_name(a, b, n):
    return f'{a}_{b}_{n}.tif'


##
def get_canvas_name(a, b, n):
    return f'{a}/{b}/{n}'


##
def get_all_canvas_keys():
    return [
        ('1kami', '1efuda', 1),
        ('1kami', '1efuda', 2),
        ('1kami', '1efuda', 3),
        ('1kami', '1efuda', 4),
        ('2shimo', '1efuda', 1),
        ('2shimo', '1efuda', 2),
        ('2shimo', '1efuda', 3),
        ('2shimo', '1efuda', 4),
        ('2shimo', '2jifuda', 1),
        ('2shimo', '2jifuda', 2),
        ('2shimo', '2jifuda', 3),
        ('2shimo', '2jifuda', 4),
    ]


## 
def get_canvas_uri(collection_name, canvas_name):
    return f'{IIIF_SERVICE_URI}{collection_name}/canvas/{canvas_name}'


##
def get_manifest_uri(collection_name):
    return f'{IIIF_SERVICE_URI}{collection_name}/manifest.json'


##
def get_image_service_uri(image_name):
    return f'{IIIF_SERVICE_URI}v2/image/{image_name}'


##
def get_image_metadata():
    return [
        {
            'label': 'Author',
            'value': 'Unknown',
        },
        {
            'label': 'Published',
            'value': 'Unknown',
        },
    ]


##
def get_image_annotation(a, b, n):
    image_name = get_image_name(a, b, n)
    image_uri = get_image_service_uri(image_name)
    collection_name = get_collection_name()
    canvas_name = get_canvas_name(a, b, n)
    return {
        '@id': '',
        '@type': 'oa:Annotation',
        'motivation': 'sc:painting',
        'resource': {
            '@id': image_uri + '/full/full/0/default.jpg',
            '@type': 'dctypes:Image',
            'format': 'image/jpeg',
            'height': HEIGHT,
            'width': WIDTH,
            'service': {
                '@context': IIIF_IMAGE_CONTEXT,
                '@id': image_uri,
                'profile': IIIF_IMAGE_API_2,
            },
        },
        'on': get_canvas_uri(collection_name, canvas_name),
    }


## Get JSON-like object for a thumbnail
def get_thumbnail(image_name, width, height):
    image_uri = get_image_service_uri(image_name)
    return {
        '@id': image_uri + f'/full/{width},{height}/0/default.jpg',
        'service': {
            '@context': IIIF_IMAGE_CONTEXT,
            '@id': image_uri,
            'profile': IIIF_IMAGE_API_2,
        },
    }


## Get JSON-like object for a canvas
def get_canvas(a, b, n):
    collection_name = get_collection_name()
    canvas_name = get_canvas_name(a, b, n)
    image_name = get_image_name(a, b, n)
    return {
        '@id': get_canvas_uri(collection_name, canvas_name),
        '@type': 'sc:Canvas',
        'label': f'{a} {b} {n}',
        'height': HEIGHT,
        'width': WIDTH,
        'thumbnail': get_thumbnail(image_name, 100, 100),
        'images': [
            get_image_annotation(a, b, n),
        ],
    }


## Get JSON-like object for a manifest
def get_manifest():
    collection_name = get_collection_name()
    canvases = [get_canvas(a, b, n) for a, b, n in get_all_canvas_keys()]
    image_names = [get_image_name(a, b, n) for a, b, n in get_all_canvas_keys()]
    return {
        '@context': IIIF_PRESENTATION_CONTEXT,
        '@id': get_manifest_uri(collection_name),
        '@type': 'sc:Manifest',
        'label': f'百人一首かるた 2020 年度 作業用',
        'metadata': get_image_metadata(),
        'description': f'百人一首かるた',
        'thumbnail': get_thumbnail(image_names[0], 100, 100),
        #'viewingDirection': 'right-to-left',
        'attribution': 'Doshisha University Library',
        'sequences': [{
            '@type': 'sc:Sequence',
            'canvases': canvases,
        }]
    }


class BaseRequestHandler(tornado.web.RequestHandler):
    def write_json(self, obj):
        if 'Accept' in self.request.headers and self.request.headers['Accept'] == '*/*':
            self.set_header('Content-Type', 'application/ld+json')
        else:
            self.set_header('Content-Type', 'application/json')
        #self.set_header('Access-Control-Allow-Origin', response.headers['*'])
        self.write(json.dumps(obj))


class Hyaku2020CanvasHandler(BaseRequestHandler):
    def get(self, a, b, n):
        n = int(n)
        obj = get_canvas(a, b, n)
        self.write_json(obj)


class Hyaku2020ManifestHandler(BaseRequestHandler):
    def get(self):
        obj = get_manifest()
        self.write_json(obj)


canvas_handler = (r'/hyaku2020/canvas/(\w+)/(\w+)/(\d+)', Hyaku2020CanvasHandler)
manifest_handler = (r'/hyaku2020/manifest\.json', Hyaku2020ManifestHandler)
