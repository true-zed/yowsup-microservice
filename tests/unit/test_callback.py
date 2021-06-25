import os
import base64
import unittest

import logging
from src.callback import CallbackSender

from unittest import TestCase


class TestCallbackSender(TestCase):

    def setUp(self) -> None:
        self.test_cs = CallbackSender(
            url='http://localhost:8002/api/',
            login='zed',
            pwd='123'
        )

    def test_get_jwt(self):
        self.assertTrue(self.test_cs._jwt)
        self.assertTrue(self.test_cs._jwt_refresh)

    def test_refresh_jwt(self):
        self.assertNotEqual(self.test_cs._get_jwt(), self.test_cs._refresh_jwt())

    def test_get_headers(self):
        headers = self.test_cs._get_headers()
        self.assertEqual(headers.get('Authorization'), 'JWT {}'.format(self.test_cs._jwt))
        self.assertEqual(headers.get('Content-Type'), 'application/json; charset=utf-8')


class PrepareFilesTests(TestCase):
    UNIT_TESTS_DIR = os.path.dirname(__file__)

    def setUp(self) -> None:
        super(PrepareFilesTests, self).setUp()
        self.test_cs = CallbackSender(
            url='http://localhost:8002/api/',
            login='zed',
            pwd='123'
        )
        self.test_files_origin = {
            'document': open(os.path.join(self.UNIT_TESTS_DIR, 'test_data/test_document.txt'), mode='rb').read(),
            'image': open(os.path.join(self.UNIT_TESTS_DIR, 'test_data/test_image.jpeg'), mode='rb').read()


        }
        self.test_files = {
            'document': {
                'url': 'https://mmg.whatsapp.net/d/f/ArV6PsIhbyQ2h8j9iTZSif_YJTZru3qIeNHKdqAHNu-0.enc',
                'ref_key': b'jRRKMXQ2TMmna0PWeOq/w6lUMM2H+4Xj/huKKVyn408=', 'media_type': 'document',
                'filename': 'test_document.txt'
            },
            'image': {
                'url': 'https://mmg.whatsapp.net/d/f/AoO9yQHaqdr-YELwc0BFplUWF6BYiWjQYo-pxUIVUfvA.enc',
                'ref_key': b'gzQVdCgRG+NTXlxbep7y9ttgqOcbkUo2duaq6ANt8ck=',
                'mimetype': 'image/jpeg', 'media_type': 'image'},
        }

    def test_image(self):
        test_file = self.test_cs._prepare_files(self.test_files.get('image')).get('msg_media')[1]
        origin_file = self.test_files_origin.get('image')
        self.assertEqual(test_file, origin_file)

    def test_document(self):
        test_file = self.test_cs._prepare_files(self.test_files.get('document')).get('msg_media')[1].decode()
        origin_file = self.test_files_origin.get('document').decode()
        self.assertEqual(test_file, origin_file)


class GenerateFilenameTests(TestCase):
    def setUp(self) -> None:
        super(GenerateFilenameTests, self).setUp()
        self.test_cs = CallbackSender(
            url='http://localhost:8002/api/',
            login='zed',
            pwd='123'
        )

    def test_document_name(self):
        self.assertNotEquals(self.test_cs.generate_document_filename('test_document.txt'), 'test_document.txt')


if __name__ == '__main__':
    unittest.main()
