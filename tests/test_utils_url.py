import warnings

import pytest

from scrapy.linkextractors import IGNORED_EXTENSIONS
from scrapy.spiders import Spider
from scrapy.utils.misc import arg_to_iter
from scrapy.utils.url import (  # type: ignore[attr-defined]
    _is_filesystem_path,
    _public_w3lib_objects,
    add_http_if_no_scheme,
    guess_scheme,
    strip_url,
    url_has_any_extension,
    url_is_from_any_domain,
    url_is_from_spider,
)


class TestUrlUtils:
    def test_url_is_from_any_domain(self):
        url = "http://www.wheele-bin-art.co.uk/get/product/123"
        assert url_is_from_any_domain(url, ["wheele-bin-art.co.uk"])
        assert not url_is_from_any_domain(url, ["art.co.uk"])

        url = "http://wheele-bin-art.co.uk/get/product/123"
        assert url_is_from_any_domain(url, ["wheele-bin-art.co.uk"])
        assert not url_is_from_any_domain(url, ["art.co.uk"])

        url = "http://www.Wheele-Bin-Art.co.uk/get/product/123"
        assert url_is_from_any_domain(url, ["wheele-bin-art.CO.UK"])
        assert url_is_from_any_domain(url, ["WHEELE-BIN-ART.CO.UK"])

        url = "http://192.169.0.15:8080/mypage.html"
        assert url_is_from_any_domain(url, ["192.169.0.15:8080"])
        assert not url_is_from_any_domain(url, ["192.169.0.15"])

        url = (
            "javascript:%20document.orderform_2581_1190810811.mode.value=%27add%27;%20"
            "javascript:%20document.orderform_2581_1190810811.submit%28%29"
        )
        assert not url_is_from_any_domain(url, ["testdomain.com"])
        assert not url_is_from_any_domain(url + ".testdomain.com", ["testdomain.com"])

    def test_url_is_from_spider(self):
        spider = Spider(name="example.com")
        assert url_is_from_spider("http://www.example.com/some/page.html", spider)
        assert url_is_from_spider("http://sub.example.com/some/page.html", spider)
        assert not url_is_from_spider("http://www.example.org/some/page.html", spider)
        assert not url_is_from_spider("http://www.example.net/some/page.html", spider)

    def test_url_is_from_spider_class_attributes(self):
        class MySpider(Spider):
            name = "example.com"

        assert url_is_from_spider("http://www.example.com/some/page.html", MySpider)
        assert url_is_from_spider("http://sub.example.com/some/page.html", MySpider)
        assert not url_is_from_spider("http://www.example.org/some/page.html", MySpider)
        assert not url_is_from_spider("http://www.example.net/some/page.html", MySpider)

    def test_url_is_from_spider_with_allowed_domains(self):
        spider = Spider(
            name="example.com", allowed_domains=["example.org", "example.net"]
        )
        assert url_is_from_spider("http://www.example.com/some/page.html", spider)
        assert url_is_from_spider("http://sub.example.com/some/page.html", spider)
        assert url_is_from_spider("http://example.com/some/page.html", spider)
        assert url_is_from_spider("http://www.example.org/some/page.html", spider)
        assert url_is_from_spider("http://www.example.net/some/page.html", spider)
        assert not url_is_from_spider("http://www.example.us/some/page.html", spider)

        spider = Spider(
            name="example.com", allowed_domains={"example.com", "example.net"}
        )
        assert url_is_from_spider("http://www.example.com/some/page.html", spider)

        spider = Spider(
            name="example.com", allowed_domains=("example.com", "example.net")
        )
        assert url_is_from_spider("http://www.example.com/some/page.html", spider)

    def test_url_is_from_spider_with_allowed_domains_class_attributes(self):
        class MySpider(Spider):
            name = "example.com"
            allowed_domains = ("example.org", "example.net")

        assert url_is_from_spider("http://www.example.com/some/page.html", MySpider)
        assert url_is_from_spider("http://sub.example.com/some/page.html", MySpider)
        assert url_is_from_spider("http://example.com/some/page.html", MySpider)
        assert url_is_from_spider("http://www.example.org/some/page.html", MySpider)
        assert url_is_from_spider("http://www.example.net/some/page.html", MySpider)
        assert not url_is_from_spider("http://www.example.us/some/page.html", MySpider)

    def test_url_has_any_extension(self):
        deny_extensions = {"." + e for e in arg_to_iter(IGNORED_EXTENSIONS)}
        assert url_has_any_extension(
            "http://www.example.com/archive.tar.gz", deny_extensions
        )
        assert url_has_any_extension("http://www.example.com/page.doc", deny_extensions)
        assert url_has_any_extension("http://www.example.com/page.pdf", deny_extensions)
        assert not url_has_any_extension(
            "http://www.example.com/page.htm", deny_extensions
        )
        assert not url_has_any_extension("http://www.example.com/", deny_extensions)
        assert not url_has_any_extension(
            "http://www.example.com/page.doc.html", deny_extensions
        )


class TestAddHttpIfNoScheme:
    def test_add_scheme(self):
        assert add_http_if_no_scheme("www.example.com") == "http://www.example.com"

    def test_without_subdomain(self):
        assert add_http_if_no_scheme("example.com") == "http://example.com"

    def test_path(self):
        assert (
            add_http_if_no_scheme("www.example.com/some/page.html")
            == "http://www.example.com/some/page.html"
        )

    def test_port(self):
        assert (
            add_http_if_no_scheme("www.example.com:80") == "http://www.example.com:80"
        )

    def test_fragment(self):
        assert (
            add_http_if_no_scheme("www.example.com/some/page#frag")
            == "http://www.example.com/some/page#frag"
        )

    def test_query(self):
        assert (
            add_http_if_no_scheme("www.example.com/do?a=1&b=2&c=3")
            == "http://www.example.com/do?a=1&b=2&c=3"
        )

    def test_username_password(self):
        assert (
            add_http_if_no_scheme("username:password@www.example.com")
            == "http://username:password@www.example.com"
        )

    def test_complete_url(self):
        assert (
            add_http_if_no_scheme(
                "username:password@www.example.com:80/some/page/do?a=1&b=2&c=3#frag"
            )
            == "http://username:password@www.example.com:80/some/page/do?a=1&b=2&c=3#frag"
        )

    def test_preserve_http(self):
        assert (
            add_http_if_no_scheme("http://www.example.com") == "http://www.example.com"
        )

    def test_preserve_http_without_subdomain(self):
        assert add_http_if_no_scheme("http://example.com") == "http://example.com"

    def test_preserve_http_path(self):
        assert (
            add_http_if_no_scheme("http://www.example.com/some/page.html")
            == "http://www.example.com/some/page.html"
        )

    def test_preserve_http_port(self):
        assert (
            add_http_if_no_scheme("http://www.example.com:80")
            == "http://www.example.com:80"
        )

    def test_preserve_http_fragment(self):
        assert (
            add_http_if_no_scheme("http://www.example.com/some/page#frag")
            == "http://www.example.com/some/page#frag"
        )

    def test_preserve_http_query(self):
        assert (
            add_http_if_no_scheme("http://www.example.com/do?a=1&b=2&c=3")
            == "http://www.example.com/do?a=1&b=2&c=3"
        )

    def test_preserve_http_username_password(self):
        assert (
            add_http_if_no_scheme("http://username:password@www.example.com")
            == "http://username:password@www.example.com"
        )

    def test_preserve_http_complete_url(self):
        assert (
            add_http_if_no_scheme(
                "http://username:password@www.example.com:80/some/page/do?a=1&b=2&c=3#frag"
            )
            == "http://username:password@www.example.com:80/some/page/do?a=1&b=2&c=3#frag"
        )

    def test_protocol_relative(self):
        assert add_http_if_no_scheme("//www.example.com") == "http://www.example.com"

    def test_protocol_relative_without_subdomain(self):
        assert add_http_if_no_scheme("//example.com") == "http://example.com"

    def test_protocol_relative_path(self):
        assert (
            add_http_if_no_scheme("//www.example.com/some/page.html")
            == "http://www.example.com/some/page.html"
        )

    def test_protocol_relative_port(self):
        assert (
            add_http_if_no_scheme("//www.example.com:80") == "http://www.example.com:80"
        )

    def test_protocol_relative_fragment(self):
        assert (
            add_http_if_no_scheme("//www.example.com/some/page#frag")
            == "http://www.example.com/some/page#frag"
        )

    def test_protocol_relative_query(self):
        assert (
            add_http_if_no_scheme("//www.example.com/do?a=1&b=2&c=3")
            == "http://www.example.com/do?a=1&b=2&c=3"
        )

    def test_protocol_relative_username_password(self):
        assert (
            add_http_if_no_scheme("//username:password@www.example.com")
            == "http://username:password@www.example.com"
        )

    def test_protocol_relative_complete_url(self):
        assert (
            add_http_if_no_scheme(
                "//username:password@www.example.com:80/some/page/do?a=1&b=2&c=3#frag"
            )
            == "http://username:password@www.example.com:80/some/page/do?a=1&b=2&c=3#frag"
        )

    def test_preserve_https(self):
        assert (
            add_http_if_no_scheme("https://www.example.com")
            == "https://www.example.com"
        )

    def test_preserve_ftp(self):
        assert add_http_if_no_scheme("ftp://www.example.com") == "ftp://www.example.com"


class TestGuessScheme:
    pass


def create_guess_scheme_t(args):
    def do_expected(self):
        url = guess_scheme(args[0])
        assert url.startswith(args[1]), (
            f"Wrong scheme guessed: for `{args[0]}` got `{url}`, expected `{args[1]}...`"
        )

    return do_expected


def create_skipped_scheme_t(args):
    def do_expected(self):
        pytest.skip(args[2])

    return do_expected


for k, args in enumerate(
    [
        ("/index", "file://"),
        ("/index.html", "file://"),
        ("./index.html", "file://"),
        ("../index.html", "file://"),
        ("../../index.html", "file://"),
        ("./data/index.html", "file://"),
        (".hidden/data/index.html", "file://"),
        ("/home/user/www/index.html", "file://"),
        ("//home/user/www/index.html", "file://"),
        ("file:///home/user/www/index.html", "file://"),
        ("index.html", "http://"),
        ("example.com", "http://"),
        ("www.example.com", "http://"),
        ("www.example.com/index.html", "http://"),
        ("http://example.com", "http://"),
        ("http://example.com/index.html", "http://"),
        ("localhost", "http://"),
        ("localhost/index.html", "http://"),
        # some corner cases (default to http://)
        ("/", "http://"),
        (".../test", "http://"),
    ],
    start=1,
):
    t_method = create_guess_scheme_t(args)
    t_method.__name__ = f"test_uri_{k:03}"
    setattr(TestGuessScheme, t_method.__name__, t_method)

# TODO: the following tests do not pass with current implementation
for k, skip_args in enumerate(
    [
        (
            r"C:\absolute\path\to\a\file.html",
            "file://",
            "Windows filepath are not supported for scrapy shell",
        ),
    ],
    start=1,
):
    t_method = create_skipped_scheme_t(skip_args)
    t_method.__name__ = f"test_uri_skipped_{k:03}"
    setattr(TestGuessScheme, t_method.__name__, t_method)


class TestStripUrl:
    def test_noop(self):
        assert (
            strip_url("http://www.example.com/index.html")
            == "http://www.example.com/index.html"
        )

    def test_noop_query_string(self):
        assert (
            strip_url("http://www.example.com/index.html?somekey=somevalue")
            == "http://www.example.com/index.html?somekey=somevalue"
        )

    def test_fragments(self):
        assert (
            strip_url(
                "http://www.example.com/index.html?somekey=somevalue#section",
                strip_fragment=False,
            )
            == "http://www.example.com/index.html?somekey=somevalue#section"
        )

    def test_path(self):
        for input_url, origin, output_url in [
            ("http://www.example.com/", False, "http://www.example.com/"),
            ("http://www.example.com", False, "http://www.example.com"),
            ("http://www.example.com", True, "http://www.example.com/"),
        ]:
            assert strip_url(input_url, origin_only=origin) == output_url

    def test_credentials(self):
        for i, o in [
            (
                "http://username@www.example.com/index.html?somekey=somevalue#section",
                "http://www.example.com/index.html?somekey=somevalue",
            ),
            (
                "https://username:@www.example.com/index.html?somekey=somevalue#section",
                "https://www.example.com/index.html?somekey=somevalue",
            ),
            (
                "ftp://username:password@www.example.com/index.html?somekey=somevalue#section",
                "ftp://www.example.com/index.html?somekey=somevalue",
            ),
        ]:
            assert strip_url(i, strip_credentials=True) == o

    def test_credentials_encoded_delims(self):
        for i, o in [
            # user: "username@"
            # password: none
            (
                "http://username%40@www.example.com/index.html?somekey=somevalue#section",
                "http://www.example.com/index.html?somekey=somevalue",
            ),
            # user: "username:pass"
            # password: ""
            (
                "https://username%3Apass:@www.example.com/index.html?somekey=somevalue#section",
                "https://www.example.com/index.html?somekey=somevalue",
            ),
            # user: "me"
            # password: "user@domain.com"
            (
                "ftp://me:user%40domain.com@www.example.com/index.html?somekey=somevalue#section",
                "ftp://www.example.com/index.html?somekey=somevalue",
            ),
        ]:
            assert strip_url(i, strip_credentials=True) == o

    def test_default_ports_creds_off(self):
        for i, o in [
            (
                "http://username:password@www.example.com:80/index.html?somekey=somevalue#section",
                "http://www.example.com/index.html?somekey=somevalue",
            ),
            (
                "http://username:password@www.example.com:8080/index.html#section",
                "http://www.example.com:8080/index.html",
            ),
            (
                "http://username:password@www.example.com:443/index.html?somekey=somevalue&someotherkey=sov#section",
                "http://www.example.com:443/index.html?somekey=somevalue&someotherkey=sov",
            ),
            (
                "https://username:password@www.example.com:443/index.html",
                "https://www.example.com/index.html",
            ),
            (
                "https://username:password@www.example.com:442/index.html",
                "https://www.example.com:442/index.html",
            ),
            (
                "https://username:password@www.example.com:80/index.html",
                "https://www.example.com:80/index.html",
            ),
            (
                "ftp://username:password@www.example.com:21/file.txt",
                "ftp://www.example.com/file.txt",
            ),
            (
                "ftp://username:password@www.example.com:221/file.txt",
                "ftp://www.example.com:221/file.txt",
            ),
        ]:
            assert strip_url(i) == o

    def test_default_ports(self):
        for i, o in [
            (
                "http://username:password@www.example.com:80/index.html",
                "http://username:password@www.example.com/index.html",
            ),
            (
                "http://username:password@www.example.com:8080/index.html",
                "http://username:password@www.example.com:8080/index.html",
            ),
            (
                "http://username:password@www.example.com:443/index.html",
                "http://username:password@www.example.com:443/index.html",
            ),
            (
                "https://username:password@www.example.com:443/index.html",
                "https://username:password@www.example.com/index.html",
            ),
            (
                "https://username:password@www.example.com:442/index.html",
                "https://username:password@www.example.com:442/index.html",
            ),
            (
                "https://username:password@www.example.com:80/index.html",
                "https://username:password@www.example.com:80/index.html",
            ),
            (
                "ftp://username:password@www.example.com:21/file.txt",
                "ftp://username:password@www.example.com/file.txt",
            ),
            (
                "ftp://username:password@www.example.com:221/file.txt",
                "ftp://username:password@www.example.com:221/file.txt",
            ),
        ]:
            assert strip_url(i, strip_default_port=True, strip_credentials=False) == o

    def test_default_ports_keep(self):
        for i, o in [
            (
                "http://username:password@www.example.com:80/index.html?somekey=somevalue&someotherkey=sov#section",
                "http://username:password@www.example.com:80/index.html?somekey=somevalue&someotherkey=sov",
            ),
            (
                "http://username:password@www.example.com:8080/index.html?somekey=somevalue&someotherkey=sov#section",
                "http://username:password@www.example.com:8080/index.html?somekey=somevalue&someotherkey=sov",
            ),
            (
                "http://username:password@www.example.com:443/index.html",
                "http://username:password@www.example.com:443/index.html",
            ),
            (
                "https://username:password@www.example.com:443/index.html",
                "https://username:password@www.example.com:443/index.html",
            ),
            (
                "https://username:password@www.example.com:442/index.html",
                "https://username:password@www.example.com:442/index.html",
            ),
            (
                "https://username:password@www.example.com:80/index.html",
                "https://username:password@www.example.com:80/index.html",
            ),
            (
                "ftp://username:password@www.example.com:21/file.txt",
                "ftp://username:password@www.example.com:21/file.txt",
            ),
            (
                "ftp://username:password@www.example.com:221/file.txt",
                "ftp://username:password@www.example.com:221/file.txt",
            ),
        ]:
            assert strip_url(i, strip_default_port=False, strip_credentials=False) == o

    def test_origin_only(self):
        for i, o in [
            (
                "http://username:password@www.example.com/index.html",
                "http://www.example.com/",
            ),
            (
                "http://username:password@www.example.com:80/foo/bar?query=value#somefrag",
                "http://www.example.com/",
            ),
            (
                "http://username:password@www.example.com:8008/foo/bar?query=value#somefrag",
                "http://www.example.com:8008/",
            ),
            (
                "https://username:password@www.example.com:443/index.html",
                "https://www.example.com/",
            ),
        ]:
            assert strip_url(i, origin_only=True) == o


class TestIsPath:
    def test_path(self):
        for input_value, output_value in (
            # https://en.wikipedia.org/wiki/Path_(computing)#Representations_of_paths_by_operating_system_and_shell
            # Unix-like OS, Microsoft Windows / cmd.exe
            ("/home/user/docs/Letter.txt", True),
            ("./inthisdir", True),
            ("../../greatgrandparent", True),
            ("~/.rcinfo", True),
            (r"C:\user\docs\Letter.txt", True),
            ("/user/docs/Letter.txt", True),
            (r"C:\Letter.txt", True),
            (r"\\Server01\user\docs\Letter.txt", True),
            (r"\\?\UNC\Server01\user\docs\Letter.txt", True),
            (r"\\?\C:\user\docs\Letter.txt", True),
            (r"C:\user\docs\somefile.ext:alternate_stream_name", True),
            (r"https://example.com", False),
        ):
            assert _is_filesystem_path(input_value) == output_value, input_value


@pytest.mark.parametrize(
    "obj_name",
    [
        "_unquotepath",
        "_safe_chars",
        "parse_url",
        *_public_w3lib_objects,
    ],
)
def test_deprecated_imports_from_w3lib(obj_name):
    with warnings.catch_warnings(record=True) as warns:
        obj_type = "attribute" if obj_name == "_safe_chars" else "function"
        message = f"The scrapy.utils.url.{obj_name} {obj_type} is deprecated, use w3lib.url.{obj_name} instead."

        from importlib import import_module

        getattr(import_module("scrapy.utils.url"), obj_name)

        assert message in warns[0].message.args
