from unittest import TestCase

from mock import patch

import settings
from regparser.layer.graphics import Graphics, gid_to_url
from regparser.test_utils.http_mixin import HttpMixin
from regparser.tree.struct import Node


class LayerGraphicsTest(HttpMixin, TestCase):
    def setUp(self):
        super(LayerGraphicsTest, self).setUp()
        self.default_url = settings.DEFAULT_IMAGE_URL
        settings.DEFAULT_IMAGE_URL = 'http://example.com/%s.gif'

    def tearDown(self):
        super(LayerGraphicsTest, self).tearDown()
        settings.DEFAULT_IMAGE_URL = self.default_url

    def test_process(self):
        node = Node("Testing ![ex](ABCD) then some more XXX " +
                    "some more ![222](XXX) followed by ![ex](ABCD) and XXX " +
                    "and ![](NOTEXT)")
        g = Graphics(None)
        for gid in ('ABCD', 'XXX', 'NOTEXT'):
            self.expect_http(uri='http://example.com/{0}.gif'.format(gid),
                             method='HEAD')
            self.expect_http(
                uri='http://example.com/{0}.thumb.gif'.format(gid),
                method='HEAD')

        result = g.process(node)
        self.assertEqual(3, len(result))
        found = [False, False, False]
        for res in result:
            if (res['text'] == '![ex](ABCD)' and
                'ABCD' in res['url'] and
                res['alt'] == 'ex' and
                    res['locations'] == [0, 1]):
                found[0] = True
            elif (res['text'] == '![222](XXX)' and
                  'XXX' in res['url'] and
                  res['alt'] == '222' and
                  res['locations'] == [0]):
                found[1] = True
            elif (res['text'] == '![](NOTEXT)' and
                  'NOTEXT' in res['url'] and
                  res['alt'] == '' and
                  res['locations'] == [0]):
                found[2] = True

        self.assertEqual([True, True, True], found)

    def test_process_format(self):
        node = Node("![A88 Something](ER22MY13.257-1)")
        g = Graphics(None)
        self.expect_http(uri='http://example.com/ER22MY13.257-1.gif',
                         method='HEAD')
        self.expect_http(uri='http://example.com/ER22MY13.257-1.thumb.gif',
                         method='HEAD')

        self.assertEqual(1, len(g.process(node)))

    @patch('regparser.layer.graphics.content')
    def test_process_custom_url(self, content):
        img_url = 'http://example.com/img1.gif'
        imga_url = 'http://example2.com/AAA.gif'
        imgf_url = 'http://example2.com/F8.gif'
        content.ImageOverrides.return_value = {'a': imga_url, 'f': imgf_url}

        node = Node("![Alt1](img1)   ![Alt2](f)  ![Alt3](a)")
        g = Graphics(None)
        for url in (img_url, imga_url, imgf_url):
            self.expect_http(uri=url, method='HEAD')
            self.expect_http(uri=url[:-3] + 'thumb.gif', method='HEAD')

        results = g.process(node)
        self.assertEqual(3, len(results))
        results = {(r['alt'], r['url']) for r in results}
        self.assertIn(('Alt1', img_url), results)
        self.assertIn(('Alt2', imgf_url), results)
        self.assertIn(('Alt3', imga_url), results)

    def test_find_thumb(self):
        """When trying to find a thumbnail, first try HEAD, then GET"""
        node = Node("![alt1](img1)")
        g = Graphics(None)
        thumb_url = settings.DEFAULT_IMAGE_URL % 'img1.thumb'
        self.expect_http(uri='http://example.com/img1.gif', method='HEAD')

        self.expect_http(uri=thumb_url, method='HEAD')
        self.expect_http(uri=thumb_url, status=404)
        # doesn't hit GET
        self.assertEqual(g.process(node)[0].get('thumb_url'), thumb_url)

        self.expect_http(uri=thumb_url, method='HEAD', status=501)
        self.expect_http(uri=thumb_url)
        self.assertEqual(g.process(node)[0].get('thumb_url'), thumb_url)

        self.expect_http(uri=thumb_url, method='HEAD', status=501)
        self.expect_http(uri=thumb_url, status=404)
        self.assertNotIn('thumb_url', g.process(node)[0])

    def test_gid_to_url(self):
        """Verify that we fall back to lowercase"""
        self.expect_http(uri='http://example.com/ABCD123.gif', method='HEAD',
                         status=403)
        self.expect_http(uri='http://example.com/abcd123.gif', method='HEAD',
                         status=403)
        self.expect_http(uri='http://example.com/ABCD123.png', method='HEAD',
                         status=403)
        self.expect_http(uri='http://example.com/abcd123.png', method='HEAD')

        self.assertEqual(gid_to_url('ABCD123'),
                         'http://example.com/abcd123.png')
