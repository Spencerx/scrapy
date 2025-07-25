import dataclasses
import os
import random
import time
import warnings
from abc import ABC, abstractmethod
from datetime import datetime
from ftplib import FTP
from io import BytesIO
from pathlib import Path
from posixpath import split
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any
from unittest import mock
from urllib.parse import urlparse

import attr
import pytest
from itemadapter import ItemAdapter
from twisted.internet.defer import inlineCallbacks

from scrapy.http import Request, Response
from scrapy.item import Field, Item
from scrapy.pipelines.files import (
    FilesPipeline,
    FSFilesStore,
    FTPFilesStore,
    GCSFilesStore,
    S3FilesStore,
)
from scrapy.utils.test import get_crawler
from tests.mockserver.ftp import MockFTPServer

from .test_pipeline_media import _mocked_download_func


def get_gcs_content_and_delete(
    bucket: Any, path: str
) -> tuple[bytes, list[dict[str, str]], Any]:
    from google.cloud import storage  # noqa: PLC0415

    client = storage.Client(project=os.environ.get("GCS_PROJECT_ID"))
    bucket = client.get_bucket(bucket)
    blob = bucket.get_blob(path)
    content = blob.download_as_string()
    acl = list(blob.acl)  # loads acl before it will be deleted
    bucket.delete_blob(path)
    return content, acl, blob


def get_ftp_content_and_delete(
    path: str,
    host: str,
    port: int,
    username: str,
    password: str,
    use_active_mode: bool = False,
) -> bytes:
    ftp = FTP()
    ftp.connect(host, port)
    ftp.login(username, password)
    if use_active_mode:
        ftp.set_pasv(False)
    ftp_data: list[bytes] = []

    def buffer_data(data: bytes) -> None:
        ftp_data.append(data)

    ftp.retrbinary(f"RETR {path}", buffer_data)
    dirname, filename = split(path)
    ftp.cwd(dirname)
    ftp.delete(filename)
    return b"".join(ftp_data)


class TestFilesPipeline:
    def setup_method(self):
        self.tempdir = mkdtemp()
        settings_dict = {"FILES_STORE": self.tempdir}
        crawler = get_crawler(spidercls=None, settings_dict=settings_dict)
        self.pipeline = FilesPipeline.from_crawler(crawler)
        self.pipeline.download_func = _mocked_download_func
        self.pipeline.open_spider(None)

    def teardown_method(self):
        rmtree(self.tempdir)

    def test_file_path(self):
        file_path = self.pipeline.file_path
        assert (
            file_path(Request("https://dev.mydeco.com/mydeco.pdf"))
            == "full/c9b564df929f4bc635bdd19fde4f3d4847c757c5.pdf"
        )
        assert (
            file_path(
                Request(
                    "http://www.maddiebrown.co.uk///catalogue-items//image_54642_12175_95307.txt"
                )
            )
            == "full/4ce274dd83db0368bafd7e406f382ae088e39219.txt"
        )
        assert (
            file_path(
                Request("https://dev.mydeco.com/two/dirs/with%20spaces%2Bsigns.doc")
            )
            == "full/94ccc495a17b9ac5d40e3eabf3afcb8c2c9b9e1a.doc"
        )
        assert (
            file_path(
                Request(
                    "http://www.dfsonline.co.uk/get_prod_image.php?img=status_0907_mdm.jpg"
                )
            )
            == "full/4507be485f38b0da8a0be9eb2e1dfab8a19223f2.jpg"
        )
        assert (
            file_path(Request("http://www.dorma.co.uk/images/product_details/2532/"))
            == "full/97ee6f8a46cbbb418ea91502fd24176865cf39b2"
        )
        assert (
            file_path(Request("http://www.dorma.co.uk/images/product_details/2532"))
            == "full/244e0dd7d96a3b7b01f54eded250c9e272577aa1"
        )
        assert (
            file_path(
                Request("http://www.dorma.co.uk/images/product_details/2532"),
                response=Response("http://www.dorma.co.uk/images/product_details/2532"),
                info=object(),
            )
            == "full/244e0dd7d96a3b7b01f54eded250c9e272577aa1"
        )
        assert (
            file_path(
                Request(
                    "http://www.dfsonline.co.uk/get_prod_image.php?img=status_0907_mdm.jpg.bohaha"
                )
            )
            == "full/76c00cef2ef669ae65052661f68d451162829507"
        )
        assert (
            file_path(
                Request(
                    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAR0AAACxCAMAAADOHZloAAACClBMVEX/\
                                    //+F0tzCwMK76ZKQ21AMqr7oAAC96JvD5aWM2kvZ78J0N7fmAAC46Y4Ap7y"
                )
            )
            == "full/178059cbeba2e34120a67f2dc1afc3ecc09b61cb.png"
        )

    def test_fs_store(self):
        assert isinstance(self.pipeline.store, FSFilesStore)
        assert self.pipeline.store.basedir == self.tempdir

        path = "some/image/key.jpg"
        fullpath = Path(self.tempdir, "some", "image", "key.jpg")
        assert self.pipeline.store._get_filesystem_path(path) == fullpath

    @inlineCallbacks
    def test_file_not_expired(self):
        item_url = "http://example.com/file.pdf"
        item = _create_item_with_files(item_url)
        patchers = [
            mock.patch.object(FilesPipeline, "inc_stats", return_value=True),
            mock.patch.object(
                FSFilesStore,
                "stat_file",
                return_value={"checksum": "abc", "last_modified": time.time()},
            ),
            mock.patch.object(
                FilesPipeline,
                "get_media_requests",
                return_value=[_prepare_request_object(item_url)],
            ),
        ]
        for p in patchers:
            p.start()

        result = yield self.pipeline.process_item(item, None)
        assert result["files"][0]["checksum"] == "abc"
        assert result["files"][0]["status"] == "uptodate"

        for p in patchers:
            p.stop()

    @inlineCallbacks
    def test_file_expired(self):
        item_url = "http://example.com/file2.pdf"
        item = _create_item_with_files(item_url)
        patchers = [
            mock.patch.object(
                FSFilesStore,
                "stat_file",
                return_value={
                    "checksum": "abc",
                    "last_modified": time.time()
                    - (self.pipeline.expires * 60 * 60 * 24 * 2),
                },
            ),
            mock.patch.object(
                FilesPipeline,
                "get_media_requests",
                return_value=[_prepare_request_object(item_url)],
            ),
            mock.patch.object(FilesPipeline, "inc_stats", return_value=True),
        ]
        for p in patchers:
            p.start()

        result = yield self.pipeline.process_item(item, None)
        assert result["files"][0]["checksum"] != "abc"
        assert result["files"][0]["status"] == "downloaded"

        for p in patchers:
            p.stop()

    @inlineCallbacks
    def test_file_cached(self):
        item_url = "http://example.com/file3.pdf"
        item = _create_item_with_files(item_url)
        patchers = [
            mock.patch.object(FilesPipeline, "inc_stats", return_value=True),
            mock.patch.object(
                FSFilesStore,
                "stat_file",
                return_value={
                    "checksum": "abc",
                    "last_modified": time.time()
                    - (self.pipeline.expires * 60 * 60 * 24 * 2),
                },
            ),
            mock.patch.object(
                FilesPipeline,
                "get_media_requests",
                return_value=[_prepare_request_object(item_url, flags=["cached"])],
            ),
        ]
        for p in patchers:
            p.start()

        result = yield self.pipeline.process_item(item, None)
        assert result["files"][0]["checksum"] != "abc"
        assert result["files"][0]["status"] == "cached"

        for p in patchers:
            p.stop()

    def test_file_path_from_item(self):
        """
        Custom file path based on item data, overriding default implementation
        """

        class CustomFilesPipeline(FilesPipeline):
            def file_path(self, request, response=None, info=None, item=None):
                return f"full/{item.get('path')}"

        file_path = CustomFilesPipeline.from_crawler(
            get_crawler(None, {"FILES_STORE": self.tempdir})
        ).file_path
        item = {"path": "path-to-store-file"}
        request = Request("http://example.com")
        assert file_path(request, item=item) == "full/path-to-store-file"

    @pytest.mark.parametrize(
        "bad_type",
        [
            "http://example.com/file.pdf",
            ("http://example.com/file.pdf",),
            {"url": "http://example.com/file.pdf"},
            123,
            None,
        ],
    )
    def test_rejects_non_list_file_urls(self, tmp_path, bad_type):
        pipeline = FilesPipeline.from_crawler(
            get_crawler(None, {"FILES_STORE": str(tmp_path)})
        )
        item = ItemWithFiles()
        item["file_urls"] = bad_type

        with pytest.raises(TypeError, match="file_urls must be a list of URLs"):
            list(pipeline.get_media_requests(item, None))


class TestFilesPipelineFieldsMixin(ABC):
    @property
    @abstractmethod
    def item_class(self) -> Any:
        raise NotImplementedError

    def test_item_fields_default(self, tmp_path):
        url = "http://www.example.com/files/1.txt"
        item = self.item_class(name="item1", file_urls=[url])
        pipeline = FilesPipeline.from_crawler(
            get_crawler(None, {"FILES_STORE": tmp_path})
        )
        requests = list(pipeline.get_media_requests(item, None))
        assert requests[0].url == url
        results = [(True, {"url": url})]
        item = pipeline.item_completed(results, item, None)
        files = ItemAdapter(item).get("files")
        assert files == [results[0][1]]
        assert isinstance(item, self.item_class)

    def test_item_fields_override_settings(self, tmp_path):
        url = "http://www.example.com/files/1.txt"
        item = self.item_class(name="item1", custom_file_urls=[url])
        pipeline = FilesPipeline.from_crawler(
            get_crawler(
                None,
                {
                    "FILES_STORE": tmp_path,
                    "FILES_URLS_FIELD": "custom_file_urls",
                    "FILES_RESULT_FIELD": "custom_files",
                },
            )
        )
        requests = list(pipeline.get_media_requests(item, None))
        assert requests[0].url == url
        results = [(True, {"url": url})]
        item = pipeline.item_completed(results, item, None)
        custom_files = ItemAdapter(item).get("custom_files")
        assert custom_files == [results[0][1]]
        assert isinstance(item, self.item_class)


class TestFilesPipelineFieldsDict(TestFilesPipelineFieldsMixin):
    item_class = dict


class FilesPipelineTestItem(Item):
    name = Field()
    # default fields
    file_urls = Field()
    files = Field()
    # overridden fields
    custom_file_urls = Field()
    custom_files = Field()


class TestFilesPipelineFieldsItem(TestFilesPipelineFieldsMixin):
    item_class = FilesPipelineTestItem


@dataclasses.dataclass
class FilesPipelineTestDataClass:
    name: str
    # default fields
    file_urls: list = dataclasses.field(default_factory=list)
    files: list = dataclasses.field(default_factory=list)
    # overridden fields
    custom_file_urls: list = dataclasses.field(default_factory=list)
    custom_files: list = dataclasses.field(default_factory=list)


class TestFilesPipelineFieldsDataClass(TestFilesPipelineFieldsMixin):
    item_class = FilesPipelineTestDataClass


@attr.s
class FilesPipelineTestAttrsItem:
    name = attr.ib(default="")
    # default fields
    file_urls: list[str] = attr.ib(default=list)
    files: list[dict[str, str]] = attr.ib(default=list)
    # overridden fields
    custom_file_urls: list[str] = attr.ib(default=list)
    custom_files: list[dict[str, str]] = attr.ib(default=list)


class TestFilesPipelineFieldsAttrsItem(TestFilesPipelineFieldsMixin):
    item_class = FilesPipelineTestAttrsItem


class TestFilesPipelineCustomSettings:
    default_cls_settings = {
        "EXPIRES": 90,
        "FILES_URLS_FIELD": "file_urls",
        "FILES_RESULT_FIELD": "files",
    }
    file_cls_attr_settings_map = {
        ("EXPIRES", "FILES_EXPIRES", "expires"),
        ("FILES_URLS_FIELD", "FILES_URLS_FIELD", "files_urls_field"),
        ("FILES_RESULT_FIELD", "FILES_RESULT_FIELD", "files_result_field"),
    }

    def _generate_fake_settings(self, tmp_path, prefix=None):
        def random_string():
            return "".join([chr(random.randint(97, 123)) for _ in range(10)])

        settings = {
            "FILES_EXPIRES": random.randint(100, 1000),
            "FILES_URLS_FIELD": random_string(),
            "FILES_RESULT_FIELD": random_string(),
            "FILES_STORE": tmp_path,
        }
        if not prefix:
            return settings

        return {
            prefix.upper() + "_" + k if k != "FILES_STORE" else k: v
            for k, v in settings.items()
        }

    def _generate_fake_pipeline(self):
        class UserDefinedFilePipeline(FilesPipeline):
            EXPIRES = 1001
            FILES_URLS_FIELD = "alfa"
            FILES_RESULT_FIELD = "beta"

        return UserDefinedFilePipeline

    def test_different_settings_for_different_instances(self, tmp_path):
        """
        If there are different instances with different settings they should keep
        different settings.
        """
        custom_settings = self._generate_fake_settings(tmp_path)
        another_pipeline = FilesPipeline.from_crawler(
            get_crawler(None, custom_settings)
        )
        one_pipeline = FilesPipeline(tmp_path, crawler=get_crawler(None))
        for pipe_attr, settings_attr, pipe_ins_attr in self.file_cls_attr_settings_map:
            default_value = self.default_cls_settings[pipe_attr]
            assert getattr(one_pipeline, pipe_attr) == default_value
            custom_value = custom_settings[settings_attr]
            assert default_value != custom_value
            assert getattr(another_pipeline, pipe_ins_attr) == custom_value

    def test_subclass_attributes_preserved_if_no_settings(self, tmp_path):
        """
        If subclasses override class attributes and there are no special settings those values should be kept.
        """
        pipe_cls = self._generate_fake_pipeline()
        pipe = pipe_cls.from_crawler(get_crawler(None, {"FILES_STORE": tmp_path}))
        for pipe_attr, settings_attr, pipe_ins_attr in self.file_cls_attr_settings_map:
            custom_value = getattr(pipe, pipe_ins_attr)
            assert custom_value != self.default_cls_settings[pipe_attr]
            assert getattr(pipe, pipe_ins_attr) == getattr(pipe, pipe_attr)

    def test_subclass_attrs_preserved_custom_settings(self, tmp_path):
        """
        If file settings are defined but they are not defined for subclass
        settings should be preserved.
        """
        pipeline_cls = self._generate_fake_pipeline()
        settings = self._generate_fake_settings(tmp_path)
        pipeline = pipeline_cls.from_crawler(get_crawler(None, settings))
        for pipe_attr, settings_attr, pipe_ins_attr in self.file_cls_attr_settings_map:
            value = getattr(pipeline, pipe_ins_attr)
            setting_value = settings.get(settings_attr)
            assert value != self.default_cls_settings[pipe_attr]
            assert value == setting_value

    def test_no_custom_settings_for_subclasses(self, tmp_path):
        """
        If there are no settings for subclass and no subclass attributes, pipeline should use
        attributes of base class.
        """

        class UserDefinedFilesPipeline(FilesPipeline):
            pass

        user_pipeline = UserDefinedFilesPipeline.from_crawler(
            get_crawler(None, {"FILES_STORE": tmp_path})
        )
        for pipe_attr, settings_attr, pipe_ins_attr in self.file_cls_attr_settings_map:
            # Values from settings for custom pipeline should be set on pipeline instance.
            custom_value = self.default_cls_settings.get(pipe_attr.upper())
            assert getattr(user_pipeline, pipe_ins_attr) == custom_value

    def test_custom_settings_for_subclasses(self, tmp_path):
        """
        If there are custom settings for subclass and NO class attributes, pipeline should use custom
        settings.
        """

        class UserDefinedFilesPipeline(FilesPipeline):
            pass

        prefix = UserDefinedFilesPipeline.__name__.upper()
        settings = self._generate_fake_settings(tmp_path, prefix=prefix)
        user_pipeline = UserDefinedFilesPipeline.from_crawler(
            get_crawler(None, settings)
        )
        for pipe_attr, settings_attr, pipe_inst_attr in self.file_cls_attr_settings_map:
            # Values from settings for custom pipeline should be set on pipeline instance.
            custom_value = settings.get(prefix + "_" + settings_attr)
            assert custom_value != self.default_cls_settings[pipe_attr]
            assert getattr(user_pipeline, pipe_inst_attr) == custom_value

    def test_custom_settings_and_class_attrs_for_subclasses(self, tmp_path):
        """
        If there are custom settings for subclass AND class attributes
        setting keys are preferred and override attributes.
        """
        pipeline_cls = self._generate_fake_pipeline()
        prefix = pipeline_cls.__name__.upper()
        settings = self._generate_fake_settings(tmp_path, prefix=prefix)
        user_pipeline = pipeline_cls.from_crawler(get_crawler(None, settings))
        for (
            pipe_cls_attr,
            settings_attr,
            pipe_inst_attr,
        ) in self.file_cls_attr_settings_map:
            custom_value = settings.get(prefix + "_" + settings_attr)
            assert custom_value != self.default_cls_settings[pipe_cls_attr]
            assert getattr(user_pipeline, pipe_inst_attr) == custom_value

    def test_cls_attrs_with_DEFAULT_prefix(self, tmp_path):
        class UserDefinedFilesPipeline(FilesPipeline):
            DEFAULT_FILES_RESULT_FIELD = "this"
            DEFAULT_FILES_URLS_FIELD = "that"

        pipeline = UserDefinedFilesPipeline.from_crawler(
            get_crawler(None, {"FILES_STORE": tmp_path})
        )
        assert (
            pipeline.files_result_field
            == UserDefinedFilesPipeline.DEFAULT_FILES_RESULT_FIELD
        )
        assert (
            pipeline.files_urls_field
            == UserDefinedFilesPipeline.DEFAULT_FILES_URLS_FIELD
        )

    def test_user_defined_subclass_default_key_names(self, tmp_path):
        """Test situation when user defines subclass of FilesPipeline,
        but uses attribute names for default pipeline (without prefixing
        them with pipeline class name).
        """
        settings = self._generate_fake_settings(tmp_path)

        class UserPipe(FilesPipeline):
            pass

        pipeline_cls = UserPipe.from_crawler(get_crawler(None, settings))

        for pipe_attr, settings_attr, pipe_inst_attr in self.file_cls_attr_settings_map:
            expected_value = settings.get(settings_attr)
            assert getattr(pipeline_cls, pipe_inst_attr) == expected_value

    def test_file_pipeline_using_pathlike_objects(self, tmp_path):
        class CustomFilesPipelineWithPathLikeDir(FilesPipeline):
            def file_path(self, request, response=None, info=None, *, item=None):
                return Path("subdir") / Path(request.url).name

        pipeline = CustomFilesPipelineWithPathLikeDir.from_crawler(
            get_crawler(None, {"FILES_STORE": tmp_path})
        )
        request = Request("http://example.com/image01.jpg")
        assert pipeline.file_path(request) == Path("subdir/image01.jpg")

    def test_files_store_constructor_with_pathlike_object(self, tmp_path):
        fs_store = FSFilesStore(tmp_path)
        assert fs_store.basedir == str(tmp_path)


@pytest.mark.requires_botocore
class TestS3FilesStore:
    @inlineCallbacks
    def test_persist(self):
        bucket = "mybucket"
        key = "export.csv"
        uri = f"s3://{bucket}/{key}"
        buffer = mock.MagicMock()
        meta = {"foo": "bar"}
        path = ""
        content_type = "image/png"

        store = S3FilesStore(uri)
        from botocore.stub import Stubber  # noqa: PLC0415

        with Stubber(store.s3_client) as stub:
            stub.add_response(
                "put_object",
                expected_params={
                    "ACL": S3FilesStore.POLICY,
                    "Body": buffer,
                    "Bucket": bucket,
                    "CacheControl": S3FilesStore.HEADERS["Cache-Control"],
                    "ContentType": content_type,
                    "Key": key,
                    "Metadata": meta,
                },
                service_response={},
            )

            yield store.persist_file(
                path,
                buffer,
                info=None,
                meta=meta,
                headers={"Content-Type": content_type},
            )

            stub.assert_no_pending_responses()
            # The call to read does not happen with Stubber
            assert buffer.method_calls == [mock.call.seek(0)]

    @inlineCallbacks
    def test_stat(self):
        bucket = "mybucket"
        key = "export.csv"
        uri = f"s3://{bucket}/{key}"
        checksum = "3187896a9657a28163abb31667df64c8"
        last_modified = datetime(2019, 12, 1)

        store = S3FilesStore(uri)
        from botocore.stub import Stubber  # noqa: PLC0415

        with Stubber(store.s3_client) as stub:
            stub.add_response(
                "head_object",
                expected_params={
                    "Bucket": bucket,
                    "Key": key,
                },
                service_response={
                    "ETag": f'"{checksum}"',
                    "LastModified": last_modified,
                },
            )

            file_stats = yield store.stat_file("", info=None)
            assert file_stats == {
                "checksum": checksum,
                "last_modified": last_modified.timestamp(),
            }

            stub.assert_no_pending_responses()


@pytest.mark.skipif(
    "GCS_PROJECT_ID" not in os.environ, reason="GCS_PROJECT_ID not found"
)
class TestGCSFilesStore:
    @inlineCallbacks
    def test_persist(self):
        uri = os.environ.get("GCS_TEST_FILE_URI")
        if not uri:
            pytest.skip("No GCS URI available for testing")
        data = b"TestGCSFilesStore: \xe2\x98\x83"
        buf = BytesIO(data)
        meta = {"foo": "bar"}
        path = "full/filename"
        store = GCSFilesStore(uri)
        store.POLICY = "authenticatedRead"
        expected_policy = {"role": "READER", "entity": "allAuthenticatedUsers"}
        yield store.persist_file(path, buf, info=None, meta=meta, headers=None)
        s = yield store.stat_file(path, info=None)
        assert "last_modified" in s
        assert "checksum" in s
        assert s["checksum"] == "cdcda85605e46d0af6110752770dce3c"
        u = urlparse(uri)
        content, acl, blob = get_gcs_content_and_delete(u.hostname, u.path[1:] + path)
        assert content == data
        assert blob.metadata == {"foo": "bar"}
        assert blob.cache_control == GCSFilesStore.CACHE_CONTROL
        assert blob.content_type == "application/octet-stream"
        assert expected_policy in acl

    @inlineCallbacks
    def test_blob_path_consistency(self):
        """Test to make sure that paths used to store files is the same as the one used to get
        already uploaded files.
        """
        try:
            import google.cloud.storage  # noqa: F401,PLC0415
        except ModuleNotFoundError:
            pytest.skip("google-cloud-storage is not installed")
        with (
            mock.patch("google.cloud.storage"),
            mock.patch("scrapy.pipelines.files.time"),
        ):
            uri = "gs://my_bucket/my_prefix/"
            store = GCSFilesStore(uri)
            store.bucket = mock.Mock()
            path = "full/my_data.txt"
            yield store.persist_file(
                path, mock.Mock(), info=None, meta=None, headers=None
            )
            yield store.stat_file(path, info=None)
            expected_blob_path = store.prefix + path
            store.bucket.blob.assert_called_with(expected_blob_path)
            store.bucket.get_blob.assert_called_with(expected_blob_path)


class TestFTPFileStore:
    @inlineCallbacks
    def test_persist(self):
        data = b"TestFTPFilesStore: \xe2\x98\x83"
        buf = BytesIO(data)
        meta = {"foo": "bar"}
        path = "full/filename"
        with MockFTPServer() as ftp_server:
            store = FTPFilesStore(ftp_server.url("/"))
            empty_dict = yield store.stat_file(path, info=None)
            assert empty_dict == {}
            yield store.persist_file(path, buf, info=None, meta=meta, headers=None)
            stat = yield store.stat_file(path, info=None)
            assert "last_modified" in stat
            assert "checksum" in stat
            assert stat["checksum"] == "d113d66b2ec7258724a268bd88eef6b6"
            path = f"{store.basedir}/{path}"
            content = get_ftp_content_and_delete(
                path,
                store.host,
                store.port,
                store.username,
                store.password,
                store.USE_ACTIVE_MODE,
            )
        assert data == content


class ItemWithFiles(Item):
    file_urls = Field()
    files = Field()


def _create_item_with_files(*files):
    item = ItemWithFiles()
    item["file_urls"] = files
    return item


def _prepare_request_object(item_url, flags=None):
    return Request(
        item_url,
        meta={"response": Response(item_url, status=200, body=b"data", flags=flags)},
    )


# this is separate from the one in test_pipeline_media.py to specifically test FilesPipeline subclasses
class TestBuildFromCrawler:
    def setup_method(self):
        self.tempdir = mkdtemp()
        self.crawler = get_crawler(None, {"FILES_STORE": self.tempdir})

    def teardown_method(self):
        rmtree(self.tempdir)

    def test_simple(self):
        class Pipeline(FilesPipeline):
            pass

        with warnings.catch_warnings(record=True) as w:
            pipe = Pipeline.from_crawler(self.crawler)
            assert pipe.crawler == self.crawler
            assert pipe._fingerprinter
            assert len(w) == 0
            assert pipe.store

    def test_has_old_init(self):
        class Pipeline(FilesPipeline):
            def __init__(self, store_uri, download_func=None, settings=None):
                super().__init__(store_uri, download_func, settings)
                self._init_called = True

        with warnings.catch_warnings(record=True) as w:
            pipe = Pipeline.from_crawler(self.crawler)
            assert pipe.crawler == self.crawler
            assert pipe._fingerprinter
            assert len(w) == 2
            assert pipe._init_called

    def test_has_from_settings(self):
        class Pipeline(FilesPipeline):
            _from_settings_called = False

            @classmethod
            def from_settings(cls, settings):
                o = super().from_settings(settings)
                o._from_settings_called = True
                return o

        with warnings.catch_warnings(record=True) as w:
            pipe = Pipeline.from_crawler(self.crawler)
            assert pipe.crawler == self.crawler
            assert pipe._fingerprinter
            assert len(w) == 3
            assert pipe.store
            assert pipe._from_settings_called

    def test_has_from_crawler_and_init(self):
        class Pipeline(FilesPipeline):
            _from_crawler_called = False

            @classmethod
            def from_crawler(cls, crawler):
                settings = crawler.settings
                store_uri = settings["FILES_STORE"]
                o = cls(store_uri, crawler=crawler)
                o._from_crawler_called = True
                return o

        with warnings.catch_warnings(record=True) as w:
            pipe = Pipeline.from_crawler(self.crawler)
            assert pipe.crawler == self.crawler
            assert pipe._fingerprinter
            assert len(w) == 0
            assert pipe.store
            assert pipe._from_crawler_called
