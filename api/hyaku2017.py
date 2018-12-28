import json
import tornado.web

IIIF_IMAGE_CONTEXT = 'http://iiif.io/api/image/2/context.json'
IIIF_PRESENTATION_CONTEXT = 'http://iiif.io/api/presentation/2/context.json'
IIIF_IMAGE_API_2 = 'http://iiif.io/api/image/2/level2.json'
IIIF_SERVICE_URI = 'https://iiif.tiramis2.doshisha.ac.jp/'
HEIGHT = 2000
WIDTH = 2669


##
def get_collection_name(n):
    #assert 1 <= n <= 100
    return 'hyaku2017' + 'ABCDE'[(n - 1) // 20]


##
def get_image_name(n):
    ## Poem Number 1 --> 002.tif
    return f'{n+1:03d}.tif'


##
def get_canvas_name(n):
    ## Poem Number 1 --> 002.tif
    return f'{n+1:05d}'


## 
def get_canvas_uri(collection_name, canvas_name):
    return f'{IIIF_SERVICE_URI}{collection_name}/canvas/{canvas_name}'


##
def get_manifest_uri(collection_name):
    return f'{IIIF_SERVICE_URI}{collection_name}/manifest.json'


##
def get_image_service_uri(image_name):
    return f'{IIIF_SERVICE_URI}v2/image/hyaku2017/{image_name}'


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
def get_image_annotation(n):
    image_name = get_image_name(n)
    image_uri = get_image_service_uri(image_name)
    collection_name = get_collection_name(n)
    canvas_name = get_canvas_name(n)
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
def get_thumbnail(n, width, height):
    image_name = get_image_name(n)
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
def get_canvas(n):
    collection_name = get_collection_name(n)
    canvas_name = get_canvas_name(n)
    return {
        '@id': get_canvas_uri(collection_name, canvas_name),
        '@type': 'sc:Canvas',
        'label': f'card{n:03d}',
        'height': HEIGHT,
        'width': WIDTH,
        'thumbnail': get_thumbnail(n, 100, 100),
        'images': [
            get_image_annotation(n),
        ],
    }


## Get JSON-like object for a manifest
def get_manifest(collection_name):
    group = collection_name[-1]
    range_start = {'A':1,'B':21,'C':41,'D':61,'E':81}[group]
    canvases = [get_canvas(n) for n in range(range_start, range_start + 20)]
    return {
        '@context': IIIF_PRESENTATION_CONTEXT,
        '@id': get_manifest_uri(collection_name),
        '@type': 'sc:Manifest',
        'label': f'百人一首かるた 2017 年度 { group } 班作業用',
        'metadata': get_image_metadata(),
        'description': f'百人一首かるた { range_start }-{ range_start + 19 }',
        'thumbnail': get_thumbnail(range_start, 100, 100),
        'viewingDirection': 'right-to-left',
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


class Hyaku2017CanvasHandler(BaseRequestHandler):
    def get(self, collection_name, canvas):
        n = int(canvas) - 1
        obj = get_canvas(n)
        self.write_json(obj)


class Hyaku2017ManifestHandler(BaseRequestHandler):
    def get(self, collection_name):
        obj = get_manifest(collection_name)
        self.write_json(obj)


canvas_handler = (r'/(hyaku2017[A-E])/canvas/(\d+)', Hyaku2017CanvasHandler)
manifest_handler = (r'/(hyaku2017[A-E])/manifest\.json', Hyaku2017ManifestHandler)
