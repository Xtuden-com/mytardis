'''
Testing the DataFile resource in MyTardis's Tastypie-based REST API

.. moduleauthor:: Grischa Meyer <grischa@gmail.com>
.. moduleauthor:: James Wettenhall <james.wettenhall@monash.edu>
'''
import os
import tempfile

from django.test.client import Client

from ...models.datafile import DataFile, DataFileObject
from ...models.dataset import Dataset
from ...models.parameters import ParameterName
from ...models.parameters import Schema

from . import MyTardisResourceTestCase


class DataFileResourceTest(MyTardisResourceTestCase):
    def setUp(self):
        super(DataFileResourceTest, self).setUp()
        self.django_client = Client()
        self.django_client.login(username=self.username,
                                 password=self.password)
        self.testds = Dataset()
        self.testds.description = "test dataset"
        self.testds.save()
        self.testds.experiments.add(self.testexp)
        df_schema_name = "http://datafileshop.com/"
        self.test_schema = Schema(namespace=df_schema_name,
                                  type=Schema.DATAFILE)
        self.test_schema.save()
        self.test_parname1 = ParameterName(schema=self.test_schema,
                                           name="fileparameter1",
                                           data_type=ParameterName.STRING)
        self.test_parname1.save()
        self.test_parname2 = ParameterName(schema=self.test_schema,
                                           name="fileparameter2",
                                           data_type=ParameterName.NUMERIC)
        self.test_parname2.save()

        self.datafile = DataFile(dataset=self.testds,
                                 filename="testfile.txt",
                                 size="42", md5sum='bogus')
        self.datafile.save()

    def test_post_single_file(self):
        ds_id = Dataset.objects.first().id
        post_data = """{
    "dataset": "/api/v1/dataset/%d/",
    "filename": "mytestfile.txt",
    "md5sum": "930e419034038dfad994f0d2e602146c",
    "size": "8",
    "mimetype": "text/plain",
    "parameter_sets": [{
        "schema": "http://datafileshop.com/",
        "parameters": [{
            "name": "fileparameter1",
            "value": "123"
        },
        {
            "name": "fileparameter2",
            "value": "123"
        }]
    }]
}""" % ds_id

        post_file = tempfile.NamedTemporaryFile()
        file_content = b"123test\n"
        post_file.write(file_content)
        post_file.flush()
        post_file.seek(0)
        datafile_count = DataFile.objects.count()
        dfo_count = DataFileObject.objects.count()
        self.assertHttpCreated(self.django_client.post(
            '/api/v1/dataset_file/',
            data={"json_data": post_data, "attached_file": post_file}))
        self.assertEqual(datafile_count + 1, DataFile.objects.count())
        self.assertEqual(dfo_count + 1, DataFileObject.objects.count())
        new_file = DataFile.objects.order_by('-pk')[0]
        self.assertEqual(file_content, new_file.get_file().read())

    def test_shared_fs_single_file(self):
        pass

    def test_shared_fs_many_files(self):  # noqa # TODO too complex
        '''
        tests sending many files with known permanent location
        (useful for Australian Synchrotron ingestions)
        '''
        files = [{'content': b'test123\n'},
                 {'content': b'test246\n'}]
        from django.conf import settings
        for file_dict in files:
            post_file = tempfile.NamedTemporaryFile(
                dir=settings.DEFAULT_STORAGE_BASE_DIR)
            file_dict['filename'] = os.path.basename(post_file.name)
            file_dict['full_path'] = post_file.name
            post_file.write(file_dict['content'])
            post_file.flush()
            post_file.seek(0)
            file_dict['object'] = post_file

        def clumsily_build_uri(res_type, dataset):
            return '/api/v1/%s/%d/' % (res_type, dataset.id)

        def md5sum(filename):
            import hashlib
            md5 = hashlib.md5()
            with open(filename, 'rb') as file_obj:
                for chunk in iter(
                        lambda: file_obj.read(128*md5.block_size), b''):
                    md5.update(chunk)
            return md5.hexdigest()

        def guess_mime(filename):
            import magic
            mime = magic.Magic(mime=True)
            return mime.from_file(filename)

        json_data = {"objects": []}
        for file_dict in files:
            file_json = {
                'dataset': clumsily_build_uri('dataset', self.testds),
                'filename': os.path.basename(file_dict['filename']),
                'md5sum': md5sum(file_dict['full_path']),
                'size': os.path.getsize(file_dict['full_path']),
                'mimetype': guess_mime(file_dict['full_path']),
                'replicas': [{
                    'url': file_dict['filename'],
                    'location': 'default',
                    'protocol': 'file',
                }],
            }
            json_data['objects'].append(file_json)

        datafile_count = DataFile.objects.count()
        dfo_count = DataFileObject.objects.count()
        self.assertHttpAccepted(self.api_client.patch(
            '/api/v1/dataset_file/',
            data=json_data,
            authentication=self.get_credentials()))
        self.assertEqual(datafile_count + 2, DataFile.objects.count())
        self.assertEqual(dfo_count + 2, DataFileObject.objects.count())
        # fake-verify DFO, so we can access the file:
        for newdfo in DataFileObject.objects.order_by('-pk')[0:2]:
            newdfo.verified = True
            newdfo.save()
        for sent_file, new_file in zip(
                reversed(files), DataFile.objects.order_by('-pk')[0:2]):
            self.assertEqual(sent_file['content'], new_file.get_file().read())

    def test_download_file(self):
        '''
        Doesn't actually check the content downloaded yet
        Just checks if the download API endpoint responds with 200
        '''
        output = self.api_client.get(
            '/api/v1/dataset_file/%d/download/' % self.datafile.id,
            authentication=self.get_credentials())
        self.assertEqual(output.status_code, 200)
