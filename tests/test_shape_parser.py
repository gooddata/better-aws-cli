import unittest

from botocore import loaders, model

from tests._utils import _import
shape_parser = _import('bac', 'shape_parser')

SERVICE = 's3'
OPERATION = 'ListBuckets'


class TestShapeParser(unittest.TestCase):
    def setUp(self):
        self.shape = self.get_shape()
        self.parser = shape_parser.ShapeParser()

    def get_shape(self):
        loader = loaders.Loader()
        service_data = loader.load_service_model(SERVICE, 'service-2')
        shape_resolver = model.ShapeResolver(service_data.get('shapes', {}))
        operation_data = service_data['operations'][OPERATION]
        return shape_resolver.resolve_shape_ref(operation_data['output'])

    def test_parse_shape(self):
        expected = {
                'Buckets': [
                    {'CreationDate': 'CreationDate:timestamp',
                     'Name': 'BucketName:string'}
                    ],
                'Owner': {'DisplayName': 'DisplayName:string',
                          'ID': 'ID:string'}
                }
        result = self.parser.parse(self.shape)
        self.assertEqual(expected, result)
