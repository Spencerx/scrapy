.. _topics-settings:

========
Settings
========

The Scrapy settings allows you to customize the behaviour of all Scrapy
components, including the core, extensions, pipelines and spiders themselves.

The infrastructure of the settings provides a global namespace of key-value mappings
that the code can use to pull configuration values from. The settings can be
populated through different mechanisms, which are described below.

The settings are also the mechanism for selecting the currently active Scrapy
project (in case you have many).

For a list of available built-in settings see: :ref:`topics-settings-ref`.

.. _topics-settings-module-envvar:

Designating the settings
========================

When you use Scrapy, you have to tell it which settings you're using. You can
do this by using an environment variable, ``SCRAPY_SETTINGS_MODULE``.

The value of ``SCRAPY_SETTINGS_MODULE`` should be in Python path syntax, e.g.
``myproject.settings``. Note that the settings module should be on the
Python :ref:`import search path <tut-searchpath>`.

.. _populating-settings:

Populating the settings
=======================

Settings can be populated using different mechanisms, each of which has a
different precedence:

 1. :ref:`Command-line settings <cli-settings>` (highest precedence)
 2. :ref:`Spider settings <spider-settings>`
 3. :ref:`Project settings <project-settings>`
 4. :ref:`Add-on settings <addon-settings>`
 5. :ref:`Command-specific default settings <cmd-default-settings>`
 6. :ref:`Global default settings <default-settings>` (lowest precedence)

.. _cli-settings:

1. Command-line settings
------------------------

Settings set in the command line have the highest precedence, overriding any
other settings.

You can explicitly override one or more settings using the ``-s`` (or
``--set``) command-line option.

.. highlight:: sh

Example::

    scrapy crawl myspider -s LOG_LEVEL=INFO -s LOG_FILE=scrapy.log

.. _spider-settings:

2. Spider settings
------------------

:ref:`Spiders <topics-spiders>` can define their own settings that will take
precedence and override the project ones.

.. note:: :ref:`Pre-crawler settings <pre-crawler-settings>` cannot be defined
    per spider, and :ref:`reactor settings <reactor-settings>` should not have
    a different value per spider when :ref:`running multiple spiders in the
    same process <run-multiple-spiders>`.

One way to do so is by setting their :attr:`~scrapy.Spider.custom_settings`
attribute:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        custom_settings = {
            "SOME_SETTING": "some value",
        }

It's often better to implement :meth:`~scrapy.Spider.update_settings` instead,
and settings set there should use the ``"spider"`` priority explicitly:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        @classmethod
        def update_settings(cls, settings):
            super().update_settings(settings)
            settings.set("SOME_SETTING", "some value", priority="spider")

.. versionadded:: 2.11

It's also possible to modify the settings in the
:meth:`~scrapy.Spider.from_crawler` method, e.g. based on :ref:`spider
arguments <spiderargs>` or other logic:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        @classmethod
        def from_crawler(cls, crawler, *args, **kwargs):
            spider = super().from_crawler(crawler, *args, **kwargs)
            if "some_argument" in kwargs:
                spider.settings.set(
                    "SOME_SETTING", kwargs["some_argument"], priority="spider"
                )
            return spider

.. _project-settings:

3. Project settings
-------------------

Scrapy projects include a settings module, usually a file called
``settings.py``, where you should populate most settings that apply to all your
spiders.

.. seealso:: :ref:`topics-settings-module-envvar`

.. _addon-settings:

4. Add-on settings
------------------

:ref:`Add-ons <topics-addons>` can modify settings. They should do this with
``"addon"`` priority where possible.

.. _cmd-default-settings:

5. Command-specific default settings
------------------------------------

Each :ref:`Scrapy command <topics-commands>` can have its own default settings,
which override the :ref:`global default settings <default-settings>`.

Those command-specific default settings are specified in the
``default_settings`` attribute of each command class.

.. _default-settings:

6. Default global settings
--------------------------

The ``scrapy.settings.default_settings`` module defines global default values
for some :ref:`built-in settings <topics-settings-ref>`.

.. note:: :command:`startproject` generates a ``settings.py`` file that sets
    some settings to different values.

    The reference documentation of settings indicates the default value if one
    exists. If :command:`startproject` sets a value, that value is documented
    as default, and the value from ``scrapy.settings.default_settings`` is
    documented as “fallback”.


Compatibility with pickle
=========================

Setting values must be :ref:`picklable <pickle-picklable>`.

Import paths and classes
========================

.. versionadded:: 2.4.0

When a setting references a callable object to be imported by Scrapy, such as a
class or a function, there are two different ways you can specify that object:

-   As a string containing the import path of that object

-   As the object itself

For example:

.. skip: next
.. code-block:: python

   from mybot.pipelines.validate import ValidateMyItem

   ITEM_PIPELINES = {
       # passing the classname...
       ValidateMyItem: 300,
       # ...equals passing the class path
       "mybot.pipelines.validate.ValidateMyItem": 300,
   }

.. note:: Passing non-callable objects is not supported.


How to access settings
======================

.. highlight:: python

In a spider, settings are available through ``self.settings``:

.. code-block:: python

    class MySpider(scrapy.Spider):
        name = "myspider"
        start_urls = ["http://example.com"]

        def parse(self, response):
            print(f"Existing settings: {self.settings.attributes.keys()}")

.. note::
    The ``settings`` attribute is set in the base Spider class after the spider
    is initialized.  If you want to use settings before the initialization
    (e.g., in your spider's ``__init__()`` method), you'll need to override the
    :meth:`~scrapy.Spider.from_crawler` method.

:ref:`Components <topics-components>` can also :ref:`access settings
<component-settings>`.

The ``settings`` object can be used like a :class:`dict` (e.g.
``settings["LOG_ENABLED"]``). However, to support non-string setting values,
which may be passed from the command line as strings, it is recommended to use
one of the methods provided by the :class:`~scrapy.settings.Settings` API.


.. _component-priority-dictionaries:

Component priority dictionaries
===============================

A **component priority dictionary** is a :class:`dict` where keys are
:ref:`components <topics-components>` and values are component priorities. For
example:

.. skip: next
.. code-block:: python

    {
        "path.to.ComponentA": None,
        ComponentB: 100,
    }

A component can be specified either as a class object or through an import
path.

.. warning:: Component priority dictionaries are regular :class:`dict` objects.
    Be careful not to define the same component more than once, e.g. with
    different import path strings or defining both an import path and a
    :class:`type` object.

A priority can be an :class:`int` or :data:`None`.

A component with priority 1 goes *before* a component with priority 2. What
going before entails, however, depends on the corresponding setting. For
example, in the :setting:`DOWNLOADER_MIDDLEWARES` setting, components have
their
:meth:`~scrapy.downloadermiddlewares.DownloaderMiddleware.process_request`
method executed before that of later components, but have their
:meth:`~scrapy.downloadermiddlewares.DownloaderMiddleware.process_response`
method executed after that of later components.

A component with priority :data:`None` is disabled.

Some component priority dictionaries get merged with some built-in value. For
example, :setting:`DOWNLOADER_MIDDLEWARES` is merged with
:setting:`DOWNLOADER_MIDDLEWARES_BASE`. This is where :data:`None` comes in
handy, allowing you to disable a component from the base setting in the regular
setting:

.. code-block:: python

    DOWNLOADER_MIDDLEWARES = {
        "scrapy.downloadermiddlewares.offsite.OffsiteMiddleware": None,
    }


Special settings
================

The following settings work slightly differently than all other settings.

.. _pre-crawler-settings:

Pre-crawler settings
--------------------

**Pre-crawler settings** are settings used before the
:class:`~scrapy.crawler.Crawler` object is created.

These settings cannot be :ref:`set from a spider <spider-settings>`.

These settings are :setting:`SPIDER_LOADER_CLASS` and settings used by the
corresponding :ref:`component <topics-components>`, e.g.
:setting:`SPIDER_MODULES` and :setting:`SPIDER_LOADER_WARN_ONLY` for the
default component.


.. _reactor-settings:

Reactor settings
----------------

**Reactor settings** are settings tied to the :doc:`Twisted reactor
<twisted:core/howto/reactor-basics>`.

These settings can be defined from a spider. However, because only 1 reactor
can be used per process, these settings cannot use a different value per spider
when :ref:`running multiple spiders in the same process
<run-multiple-spiders>`.

In general, if different spiders define different values, the first defined
value is used. However, if two spiders request a different reactor, an
exception is raised.

These settings are:

-   :setting:`ASYNCIO_EVENT_LOOP` (not possible to set per-spider when using
    :class:`~scrapy.crawler.AsyncCrawlerProcess`, see below)

-   :setting:`DNS_RESOLVER` and settings used by the corresponding
    component, e.g. :setting:`DNSCACHE_ENABLED`, :setting:`DNSCACHE_SIZE`
    and :setting:`DNS_TIMEOUT` for the default one.

-   :setting:`REACTOR_THREADPOOL_MAXSIZE`

-   :setting:`TWISTED_REACTOR` (ignored when using
    :class:`~scrapy.crawler.AsyncCrawlerProcess`, see below)

:setting:`ASYNCIO_EVENT_LOOP` and :setting:`TWISTED_REACTOR` are used upon
installing the reactor. The rest of the settings are applied when starting
the reactor.

There is an additional restriction for :setting:`TWISTED_REACTOR` and
:setting:`ASYNCIO_EVENT_LOOP` when using
:class:`~scrapy.crawler.AsyncCrawlerProcess`: when this class is instantiated,
it installs :class:`~twisted.internet.asyncioreactor.AsyncioSelectorReactor`,
ignoring the value of :setting:`TWISTED_REACTOR` and using the value of
:setting:`ASYNCIO_EVENT_LOOP` that was passed to
:meth:`AsyncCrawlerProcess.__init__()
<scrapy.crawler.AsyncCrawlerProcess.__init__>`. If a different value for
:setting:`TWISTED_REACTOR` or :setting:`ASYNCIO_EVENT_LOOP` is provided later,
e.g. in :ref:`per-spider settings <spider-settings>`, an exception will be
raised.


.. _topics-settings-ref:

Built-in settings reference
===========================

Here's a list of all available Scrapy settings, in alphabetical order, along
with their default values and the scope where they apply.

The scope, where available, shows where the setting is being used, if it's tied
to any particular component. In that case the module of that component will be
shown, typically an extension, middleware or pipeline. It also means that the
component must be enabled in order for the setting to have any effect.

.. setting:: ADDONS

ADDONS
------

Default: ``{}``

A dict containing paths to the add-ons enabled in your project and their
priorities. For more information, see :ref:`topics-addons`.

.. setting:: AWS_ACCESS_KEY_ID

AWS_ACCESS_KEY_ID
-----------------

Default: ``None``

The AWS access key used by code that requires access to `Amazon Web services`_,
such as the :ref:`S3 feed storage backend <topics-feed-storage-s3>`.

.. setting:: AWS_SECRET_ACCESS_KEY

AWS_SECRET_ACCESS_KEY
---------------------

Default: ``None``

The AWS secret key used by code that requires access to `Amazon Web services`_,
such as the :ref:`S3 feed storage backend <topics-feed-storage-s3>`.

.. setting:: AWS_SESSION_TOKEN

AWS_SESSION_TOKEN
-----------------

Default: ``None``

The AWS security token used by code that requires access to `Amazon Web services`_,
such as the :ref:`S3 feed storage backend <topics-feed-storage-s3>`, when using
`temporary security credentials`_.

.. _temporary security credentials: https://docs.aws.amazon.com/IAM/latest/UserGuide/security-creds.html

.. setting:: AWS_ENDPOINT_URL

AWS_ENDPOINT_URL
----------------

Default: ``None``

Endpoint URL used for S3-like storage, for example Minio or s3.scality.

.. setting:: AWS_USE_SSL

AWS_USE_SSL
-----------

Default: ``None``

Use this option if you want to disable SSL connection for communication with
S3 or S3-like storage. By default SSL will be used.

.. setting:: AWS_VERIFY

AWS_VERIFY
----------

Default: ``None``

Verify SSL connection between Scrapy and S3 or S3-like storage. By default
SSL verification will occur.

.. setting:: AWS_REGION_NAME

AWS_REGION_NAME
---------------

Default: ``None``

The name of the region associated with the AWS client.

.. setting:: ASYNCIO_EVENT_LOOP

ASYNCIO_EVENT_LOOP
------------------

Default: ``None``

Import path of a given ``asyncio`` event loop class.

If the asyncio reactor is enabled (see :setting:`TWISTED_REACTOR`) this setting can be used to specify the
asyncio event loop to be used with it. Set the setting to the import path of the
desired asyncio event loop class. If the setting is set to ``None`` the default asyncio
event loop will be used.

If you are installing the asyncio reactor manually using the :func:`~scrapy.utils.reactor.install_reactor`
function, you can use the ``event_loop_path`` parameter to indicate the import path of the event loop
class to be used.

Note that the event loop class must inherit from :class:`asyncio.AbstractEventLoop`.

.. caution:: Please be aware that, when using a non-default event loop
    (either defined via :setting:`ASYNCIO_EVENT_LOOP` or installed with
    :func:`~scrapy.utils.reactor.install_reactor`), Scrapy will call
    :func:`asyncio.set_event_loop`, which will set the specified event loop
    as the current loop for the current OS thread.

.. setting:: BOT_NAME

BOT_NAME
--------

Default: ``<project name>`` (:ref:`fallback <default-settings>`: ``'scrapybot'``)

The name of the bot implemented by this Scrapy project (also known as the
project name). This name will be used for the logging too.

It's automatically populated with your project name when you create your
project with the :command:`startproject` command.

.. setting:: CONCURRENT_ITEMS

CONCURRENT_ITEMS
----------------

Default: ``100``

Maximum number of concurrent items (per response) to process in parallel in
:ref:`item pipelines <topics-item-pipeline>`.

.. setting:: CONCURRENT_REQUESTS

CONCURRENT_REQUESTS
-------------------

Default: ``16``

The maximum number of concurrent (i.e. simultaneous) requests that will be
performed by the Scrapy downloader.

.. setting:: CONCURRENT_REQUESTS_PER_DOMAIN

CONCURRENT_REQUESTS_PER_DOMAIN
------------------------------

Default: ``1`` (:ref:`fallback <default-settings>`: ``8``)

The maximum number of concurrent (i.e. simultaneous) requests that will be
performed to any single domain.

See also: :ref:`topics-autothrottle` and its
:setting:`AUTOTHROTTLE_TARGET_CONCURRENCY` option.


.. setting:: DEFAULT_DROPITEM_LOG_LEVEL

DEFAULT_DROPITEM_LOG_LEVEL
--------------------------

Default: ``"WARNING"``

Default :ref:`log level <levels>` of messages about dropped items.

When an item is dropped by raising :exc:`scrapy.exceptions.DropItem` from the
:func:`process_item` method of an :ref:`item pipeline <topics-item-pipeline>`,
a message is logged, and by default its log level is the one configured in this
setting.

You may specify this log level as an integer (e.g. ``20``), as a log level
constant (e.g. ``logging.INFO``) or as a string with the name of a log level
constant (e.g. ``"INFO"``).

When writing an item pipeline, you can force a different log level by setting
:attr:`scrapy.exceptions.DropItem.log_level` in your
:exc:`scrapy.exceptions.DropItem` exception. For example:

.. code-block:: python

   from scrapy.exceptions import DropItem


   class MyPipeline:
       def process_item(self, item, spider):
           if not item.get("price"):
               raise DropItem("Missing price data", log_level="INFO")
           return item

.. setting:: DEFAULT_ITEM_CLASS

DEFAULT_ITEM_CLASS
------------------

Default: ``'scrapy.Item'``

The default class that will be used for instantiating items in the :ref:`the
Scrapy shell <topics-shell>`.

.. setting:: DEFAULT_REQUEST_HEADERS

DEFAULT_REQUEST_HEADERS
-----------------------

Default:

.. code-block:: python

    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en",
    }

The default headers used for Scrapy HTTP Requests. They're populated in the
:class:`~scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware`.

.. caution:: Cookies set via the ``Cookie`` header are not considered by the
    :ref:`cookies-mw`. If you need to set cookies for a request, use the
    :class:`Request.cookies <scrapy.Request>` parameter. This is a known
    current limitation that is being worked on.

.. setting:: DEPTH_LIMIT

DEPTH_LIMIT
-----------

Default: ``0``

Scope: ``scrapy.spidermiddlewares.depth.DepthMiddleware``

The maximum depth that will be allowed to crawl for any site. If zero, no limit
will be imposed.

.. setting:: DEPTH_PRIORITY

DEPTH_PRIORITY
--------------

Default: ``0``

Scope: ``scrapy.spidermiddlewares.depth.DepthMiddleware``

An integer that is used to adjust the :attr:`~scrapy.Request.priority` of
a :class:`~scrapy.Request` based on its depth.

The priority of a request is adjusted as follows:

.. skip: next
.. code-block:: python

    request.priority = request.priority - (depth * DEPTH_PRIORITY)

As depth increases, positive values of ``DEPTH_PRIORITY`` decrease request
priority (BFO), while negative values increase request priority (DFO). See
also :ref:`faq-bfo-dfo`.

.. note::

    This setting adjusts priority **in the opposite way** compared to
    other priority settings :setting:`REDIRECT_PRIORITY_ADJUST`
    and :setting:`RETRY_PRIORITY_ADJUST`.

.. setting:: DEPTH_STATS_VERBOSE

DEPTH_STATS_VERBOSE
-------------------

Default: ``False``

Scope: ``scrapy.spidermiddlewares.depth.DepthMiddleware``

Whether to collect verbose depth stats. If this is enabled, the number of
requests for each depth is collected in the stats.

.. setting:: DNSCACHE_ENABLED

DNSCACHE_ENABLED
----------------

Default: ``True``

Whether to enable DNS in-memory cache.

.. setting:: DNSCACHE_SIZE

DNSCACHE_SIZE
-------------

Default: ``10000``

DNS in-memory cache size.

.. setting:: DNS_RESOLVER

DNS_RESOLVER
------------

.. versionadded:: 2.0

Default: ``'scrapy.resolver.CachingThreadedResolver'``

The class to be used to resolve DNS names. The default ``scrapy.resolver.CachingThreadedResolver``
supports specifying a timeout for DNS requests via the :setting:`DNS_TIMEOUT` setting,
but works only with IPv4 addresses. Scrapy provides an alternative resolver,
``scrapy.resolver.CachingHostnameResolver``, which supports IPv4/IPv6 addresses but does not
take the :setting:`DNS_TIMEOUT` setting into account.

.. setting:: DNS_TIMEOUT

DNS_TIMEOUT
-----------

Default: ``60``

Timeout for processing of DNS queries in seconds. Float is supported.

.. setting:: DOWNLOADER

DOWNLOADER
----------

Default: ``'scrapy.core.downloader.Downloader'``

The downloader to use for crawling.

.. setting:: DOWNLOADER_HTTPCLIENTFACTORY

DOWNLOADER_HTTPCLIENTFACTORY
----------------------------

Default: ``'scrapy.core.downloader.webclient.ScrapyHTTPClientFactory'``

Defines a Twisted ``protocol.ClientFactory``  class to use for HTTP/1.0
connections (for ``HTTP10DownloadHandler``).

.. note::

    HTTP/1.0 is rarely used nowadays and its Scrapy support is deprecated,
    so you can safely ignore this setting,
    unless you really want to use HTTP/1.0 and override
    :setting:`DOWNLOAD_HANDLERS` for ``http(s)`` scheme accordingly,
    i.e. to ``'scrapy.core.downloader.handlers.http.HTTP10DownloadHandler'``.

.. setting:: DOWNLOADER_CLIENTCONTEXTFACTORY

DOWNLOADER_CLIENTCONTEXTFACTORY
-------------------------------

Default: ``'scrapy.core.downloader.contextfactory.ScrapyClientContextFactory'``

Represents the classpath to the ContextFactory to use.

Here, "ContextFactory" is a Twisted term for SSL/TLS contexts, defining
the TLS/SSL protocol version to use, whether to do certificate verification,
or even enable client-side authentication (and various other things).

.. note::

    Scrapy default context factory **does NOT perform remote server
    certificate verification**. This is usually fine for web scraping.

    If you do need remote server certificate verification enabled,
    Scrapy also has another context factory class that you can set,
    ``'scrapy.core.downloader.contextfactory.BrowserLikeContextFactory'``,
    which uses the platform's certificates to validate remote endpoints.

If you do use a custom ContextFactory, make sure its ``__init__`` method
accepts a ``method`` parameter (this is the ``OpenSSL.SSL`` method mapping
:setting:`DOWNLOADER_CLIENT_TLS_METHOD`), a ``tls_verbose_logging``
parameter (``bool``) and a ``tls_ciphers`` parameter (see
:setting:`DOWNLOADER_CLIENT_TLS_CIPHERS`).

.. setting:: DOWNLOADER_CLIENT_TLS_CIPHERS

DOWNLOADER_CLIENT_TLS_CIPHERS
-----------------------------

Default: ``'DEFAULT'``

Use  this setting to customize the TLS/SSL ciphers used by the default
HTTP/1.1 downloader.

The setting should contain a string in the `OpenSSL cipher list format`_,
these ciphers will be used as client ciphers. Changing this setting may be
necessary to access certain HTTPS websites: for example, you may need to use
``'DEFAULT:!DH'`` for a website with weak DH parameters or enable a
specific cipher that is not included in ``DEFAULT`` if a website requires it.

.. _OpenSSL cipher list format: https://docs.openssl.org/master/man1/openssl-ciphers/#cipher-list-format

.. setting:: DOWNLOADER_CLIENT_TLS_METHOD

DOWNLOADER_CLIENT_TLS_METHOD
----------------------------

Default: ``'TLS'``

Use this setting to customize the TLS/SSL method used by the default
HTTP/1.1 downloader.

This setting must be one of these string values:

- ``'TLS'``: maps to OpenSSL's ``TLS_method()`` (a.k.a ``SSLv23_method()``),
  which allows protocol negotiation, starting from the highest supported
  by the platform; **default, recommended**
- ``'TLSv1.0'``: this value forces HTTPS connections to use TLS version 1.0 ;
  set this if you want the behavior of Scrapy<1.1
- ``'TLSv1.1'``: forces TLS version 1.1
- ``'TLSv1.2'``: forces TLS version 1.2


.. setting:: DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING

DOWNLOADER_CLIENT_TLS_VERBOSE_LOGGING
-------------------------------------

Default: ``False``

Setting this to ``True`` will enable DEBUG level messages about TLS connection
parameters after establishing HTTPS connections. The kind of information logged
depends on the versions of OpenSSL and pyOpenSSL.

This setting is only used for the default
:setting:`DOWNLOADER_CLIENTCONTEXTFACTORY`.

.. setting:: DOWNLOADER_MIDDLEWARES

DOWNLOADER_MIDDLEWARES
----------------------

Default:: ``{}``

A dict containing the downloader middlewares enabled in your project, and their
orders. For more info see :ref:`topics-downloader-middleware-setting`.

.. setting:: DOWNLOADER_MIDDLEWARES_BASE

DOWNLOADER_MIDDLEWARES_BASE
---------------------------

Default:

.. code-block:: python

    {
        "scrapy.downloadermiddlewares.offsite.OffsiteMiddleware": 50,
        "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware": 100,
        "scrapy.downloadermiddlewares.httpauth.HttpAuthMiddleware": 300,
        "scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware": 350,
        "scrapy.downloadermiddlewares.defaultheaders.DefaultHeadersMiddleware": 400,
        "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": 500,
        "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
        "scrapy.downloadermiddlewares.ajaxcrawl.AjaxCrawlMiddleware": 560,
        "scrapy.downloadermiddlewares.redirect.MetaRefreshMiddleware": 580,
        "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 590,
        "scrapy.downloadermiddlewares.redirect.RedirectMiddleware": 600,
        "scrapy.downloadermiddlewares.cookies.CookiesMiddleware": 700,
        "scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware": 750,
        "scrapy.downloadermiddlewares.stats.DownloaderStats": 850,
        "scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware": 900,
    }

A dict containing the downloader middlewares enabled by default in Scrapy. Low
orders are closer to the engine, high orders are closer to the downloader. You
should never modify this setting in your project, modify
:setting:`DOWNLOADER_MIDDLEWARES` instead.  For more info see
:ref:`topics-downloader-middleware-setting`.

.. setting:: DOWNLOADER_STATS

DOWNLOADER_STATS
----------------

Default: ``True``

Whether to enable downloader stats collection.

.. setting:: DOWNLOAD_DELAY

DOWNLOAD_DELAY
--------------

Default: ``1`` (:ref:`fallback <default-settings>`: ``0``)

Minimum seconds to wait between 2 consecutive requests to the same domain.

Use :setting:`DOWNLOAD_DELAY` to throttle your crawling speed, to avoid hitting
servers too hard.

Decimal numbers are supported. For example, to send a maximum of 4 requests
every 10 seconds::

    DOWNLOAD_DELAY = 2.5

This setting is also affected by the :setting:`RANDOMIZE_DOWNLOAD_DELAY`
setting, which is enabled by default.

Note that :setting:`DOWNLOAD_DELAY` can lower the effective per-domain
concurrency below :setting:`CONCURRENT_REQUESTS_PER_DOMAIN`. If the response
time of a domain is lower than :setting:`DOWNLOAD_DELAY`, the effective
concurrency for that domain is 1. When testing throttling configurations, it
usually makes sense to lower :setting:`CONCURRENT_REQUESTS_PER_DOMAIN` first,
and only increase :setting:`DOWNLOAD_DELAY` once
:setting:`CONCURRENT_REQUESTS_PER_DOMAIN` is 1 but a higher throttling is
desired.

.. _spider-download_delay-attribute:

.. note::

    This delay can be set per spider using :attr:`download_delay` spider attribute.

It is also possible to change this setting per domain, although it requires
non-trivial code. See the implementation of the :ref:`AutoThrottle
<topics-autothrottle>` extension for an example.


.. setting:: DOWNLOAD_HANDLERS

DOWNLOAD_HANDLERS
-----------------

Default: ``{}``

A dict containing the request downloader handlers enabled in your project.
See :setting:`DOWNLOAD_HANDLERS_BASE` for example format.

.. setting:: DOWNLOAD_HANDLERS_BASE

DOWNLOAD_HANDLERS_BASE
----------------------

Default:

.. code-block:: python

    {
        "data": "scrapy.core.downloader.handlers.datauri.DataURIDownloadHandler",
        "file": "scrapy.core.downloader.handlers.file.FileDownloadHandler",
        "http": "scrapy.core.downloader.handlers.http.HTTPDownloadHandler",
        "https": "scrapy.core.downloader.handlers.http.HTTPDownloadHandler",
        "s3": "scrapy.core.downloader.handlers.s3.S3DownloadHandler",
        "ftp": "scrapy.core.downloader.handlers.ftp.FTPDownloadHandler",
    }


A dict containing the request download handlers enabled by default in Scrapy.
You should never modify this setting in your project, modify
:setting:`DOWNLOAD_HANDLERS` instead.

You can disable any of these download handlers by assigning ``None`` to their
URI scheme in :setting:`DOWNLOAD_HANDLERS`. E.g., to disable the built-in FTP
handler (without replacement), place this in your ``settings.py``:

.. code-block:: python

    DOWNLOAD_HANDLERS = {
        "ftp": None,
    }

.. _http2:

The default HTTPS handler uses HTTP/1.1. To use HTTP/2:

#.  Install ``Twisted[http2]>=17.9.0`` to install the packages required to
    enable HTTP/2 support in Twisted.

#.  Update :setting:`DOWNLOAD_HANDLERS` as follows:

    .. code-block:: python

        DOWNLOAD_HANDLERS = {
            "https": "scrapy.core.downloader.handlers.http2.H2DownloadHandler",
        }

.. warning::

    HTTP/2 support in Scrapy is experimental, and not yet recommended for
    production environments. Future Scrapy versions may introduce related
    changes without a deprecation period or warning.

.. note::

    Known limitations of the current HTTP/2 implementation of Scrapy include:

    -   No support for HTTP/2 Cleartext (h2c), since no major browser supports
        HTTP/2 unencrypted (refer `http2 faq`_).

    -   No setting to specify a maximum `frame size`_ larger than the default
        value, 16384. Connections to servers that send a larger frame will
        fail.

    -   No support for `server pushes`_, which are ignored.

    -   No support for the :signal:`bytes_received` and
        :signal:`headers_received` signals.

.. _frame size: https://datatracker.ietf.org/doc/html/rfc7540#section-4.2
.. _http2 faq: https://http2.github.io/faq/#does-http2-require-encryption
.. _server pushes: https://datatracker.ietf.org/doc/html/rfc7540#section-8.2

.. setting:: DOWNLOAD_SLOTS

DOWNLOAD_SLOTS
--------------

Default: ``{}``

Allows to define concurrency/delay parameters on per slot (domain) basis:

    .. code-block:: python

        DOWNLOAD_SLOTS = {
            "quotes.toscrape.com": {"concurrency": 1, "delay": 2, "randomize_delay": False},
            "books.toscrape.com": {"delay": 3, "randomize_delay": False},
        }

.. note::

    For other downloader slots default settings values will be used:

    -   :setting:`DOWNLOAD_DELAY`: ``delay``
    -   :setting:`CONCURRENT_REQUESTS_PER_DOMAIN`: ``concurrency``
    -   :setting:`RANDOMIZE_DOWNLOAD_DELAY`: ``randomize_delay``


.. setting:: DOWNLOAD_TIMEOUT

DOWNLOAD_TIMEOUT
----------------

Default: ``180``

The amount of time (in secs) that the downloader will wait before timing out.

.. note::

    This timeout can be set per spider using :attr:`download_timeout`
    spider attribute and per-request using :reqmeta:`download_timeout`
    Request.meta key.

.. setting:: DOWNLOAD_MAXSIZE
.. reqmeta:: download_maxsize

DOWNLOAD_MAXSIZE
----------------

Default: ``1073741824`` (1 GiB)

The maximum response body size (in bytes) allowed. Bigger responses are
aborted and ignored.

This applies both before and after compression. If decompressing a response
body would exceed this limit, decompression is aborted and the response is
ignored.

Use ``0`` to disable this limit.

This limit can be set per spider using the :attr:`download_maxsize` spider
attribute and per request using the :reqmeta:`download_maxsize` Request.meta
key.

.. setting:: DOWNLOAD_WARNSIZE
.. reqmeta:: download_warnsize

DOWNLOAD_WARNSIZE
-----------------

Default: ``33554432`` (32 MiB)

If the size of a response exceeds this value, before or after compression, a
warning will be logged about it.

Use ``0`` to disable this limit.

This limit can be set per spider using the :attr:`download_warnsize` spider
attribute and per request using the :reqmeta:`download_warnsize` Request.meta
key.

.. setting:: DOWNLOAD_FAIL_ON_DATALOSS

DOWNLOAD_FAIL_ON_DATALOSS
-------------------------

Default: ``True``

Whether or not to fail on broken responses, that is, declared
``Content-Length`` does not match content sent by the server or chunked
response was not properly finish. If ``True``, these responses raise a
``ResponseFailed([_DataLoss])`` error. If ``False``, these responses
are passed through and the flag ``dataloss`` is added to the response, i.e.:
``'dataloss' in response.flags`` is ``True``.

Optionally, this can be set per-request basis by using the
:reqmeta:`download_fail_on_dataloss` Request.meta key to ``False``.

.. note::

  A broken response, or data loss error, may happen under several
  circumstances, from server misconfiguration to network errors to data
  corruption. It is up to the user to decide if it makes sense to process
  broken responses considering they may contain partial or incomplete content.
  If :setting:`RETRY_ENABLED` is ``True`` and this setting is set to ``True``,
  the ``ResponseFailed([_DataLoss])`` failure will be retried as usual.

.. warning::

    This setting is ignored by the
    :class:`~scrapy.core.downloader.handlers.http2.H2DownloadHandler`
    download handler (see :setting:`DOWNLOAD_HANDLERS`). In case of a data loss
    error, the corresponding HTTP/2 connection may be corrupted, affecting other
    requests that use the same connection; hence, a ``ResponseFailed([InvalidBodyLengthError])``
    failure is always raised for every request that was using that connection.

.. setting:: DUPEFILTER_CLASS

DUPEFILTER_CLASS
----------------

Default: ``'scrapy.dupefilters.RFPDupeFilter'``

The class used to detect and filter duplicate requests.

The default, :class:`~scrapy.dupefilters.RFPDupeFilter`, filters based on the
:setting:`REQUEST_FINGERPRINTER_CLASS` setting.

To change how duplicates are checked, you can point :setting:`DUPEFILTER_CLASS`
to a custom subclass of :class:`~scrapy.dupefilters.RFPDupeFilter` that
overrides its ``__init__`` method to use a :ref:`different request
fingerprinting class <custom-request-fingerprinter>`. For example:

.. code-block:: python

    from scrapy.dupefilters import RFPDupeFilter
    from scrapy.utils.request import fingerprint


    class CustomRequestFingerprinter:
        def fingerprint(self, request):
            return fingerprint(request, include_headers=["X-ID"])


    class CustomDupeFilter(RFPDupeFilter):

        def __init__(self, path=None, debug=False, *, fingerprinter=None):
            super().__init__(
                path=path, debug=debug, fingerprinter=CustomRequestFingerprinter()
            )

To disable duplicate request filtering set :setting:`DUPEFILTER_CLASS` to
``'scrapy.dupefilters.BaseDupeFilter'``. Note that not filtering out duplicate
requests may cause crawling loops. It is usually better to set
the ``dont_filter`` parameter to ``True`` on the ``__init__`` method of a
specific :class:`~scrapy.Request` object that should not be filtered out.

A class assigned to :setting:`DUPEFILTER_CLASS` must implement the following
interface::

    class MyDupeFilter:

        @classmethod
        def from_settings(cls, settings):
            """Returns an instance of this duplicate request filtering class
            based on the current crawl settings."""
            return cls()

        def request_seen(self, request):
            """Returns ``True`` if *request* is a duplicate of another request
            seen in a previous call to :meth:`request_seen`, or ``False``
            otherwise."""
            return False

        def open(self):
            """Called before the spider opens. It may return a deferred."""
            pass

        def close(self, reason):
            """Called before the spider closes. It may return a deferred."""
            pass

        def log(self, request, spider):
            """Logs that a request has been filtered out.

            It is called right after a call to :meth:`request_seen` that
            returns ``True``.

            If :meth:`request_seen` always returns ``False``, such as in the
            case of :class:`~scrapy.dupefilters.BaseDupeFilter`, this method
            may be omitted.
            """
            pass

.. autoclass:: scrapy.dupefilters.BaseDupeFilter

.. autoclass:: scrapy.dupefilters.RFPDupeFilter


.. setting:: DUPEFILTER_DEBUG

DUPEFILTER_DEBUG
----------------

Default: ``False``

By default, ``RFPDupeFilter`` only logs the first duplicate request.
Setting :setting:`DUPEFILTER_DEBUG` to ``True`` will make it log all duplicate requests.

.. setting:: EDITOR

EDITOR
------

Default: ``vi`` (on Unix systems) or the IDLE editor (on Windows)

The editor to use for editing spiders with the :command:`edit` command.
Additionally, if the ``EDITOR`` environment variable is set, the :command:`edit`
command will prefer it over the default setting.

.. setting:: EXTENSIONS

EXTENSIONS
----------

Default:: ``{}``

:ref:`Component priority dictionary <component-priority-dictionaries>` of
enabled extensions. See :ref:`topics-extensions`.

.. setting:: EXTENSIONS_BASE

EXTENSIONS_BASE
---------------

Default:

.. code-block:: python

    {
        "scrapy.extensions.corestats.CoreStats": 0,
        "scrapy.extensions.telnet.TelnetConsole": 0,
        "scrapy.extensions.memusage.MemoryUsage": 0,
        "scrapy.extensions.memdebug.MemoryDebugger": 0,
        "scrapy.extensions.closespider.CloseSpider": 0,
        "scrapy.extensions.feedexport.FeedExporter": 0,
        "scrapy.extensions.logstats.LogStats": 0,
        "scrapy.extensions.spiderstate.SpiderState": 0,
        "scrapy.extensions.throttle.AutoThrottle": 0,
    }

A dict containing the extensions available by default in Scrapy, and their
orders. This setting contains all stable built-in extensions. Keep in mind that
some of them need to be enabled through a setting.

For more information See the :ref:`extensions user guide  <topics-extensions>`
and the :ref:`list of available extensions <topics-extensions-ref>`.

.. setting:: FEED_TEMPDIR

FEED_TEMPDIR
------------

The Feed Temp dir allows you to set a custom folder to save crawler
temporary files before uploading with :ref:`FTP feed storage <topics-feed-storage-ftp>` and
:ref:`Amazon S3 <topics-feed-storage-s3>`.

.. setting:: FEED_STORAGE_GCS_ACL

FEED_STORAGE_GCS_ACL
--------------------

The Access Control List (ACL) used when storing items to :ref:`Google Cloud Storage <topics-feed-storage-gcs>`.
For more information on how to set this value, please refer to the column *JSON API* in `Google Cloud documentation <https://cloud.google.com/storage/docs/access-control/lists>`_.

.. setting:: FORCE_CRAWLER_PROCESS

FORCE_CRAWLER_PROCESS
---------------------

Default: ``False``

If ``False``, :ref:`Scrapy commands that need a CrawlerProcess
<topics-commands-crawlerprocess>` will decide between using
:class:`scrapy.crawler.AsyncCrawlerProcess` and
:class:`scrapy.crawler.CrawlerProcess` based on the value of the
:setting:`TWISTED_REACTOR` setting, but ignoring its value in :ref:`per-spider
settings <spider-settings>`.

If ``True``, these commands will always use
:class:`~scrapy.crawler.CrawlerProcess`.

Set this to ``True`` if you want to set :setting:`TWISTED_REACTOR` to a
non-default value in :ref:`per-spider settings <spider-settings>`.

.. setting:: FTP_PASSIVE_MODE

FTP_PASSIVE_MODE
----------------

Default: ``True``

Whether or not to use passive mode when initiating FTP transfers.

.. reqmeta:: ftp_password
.. setting:: FTP_PASSWORD

FTP_PASSWORD
------------

Default: ``"guest"``

The password to use for FTP connections when there is no ``"ftp_password"``
in ``Request`` meta.

.. note::
    Paraphrasing `RFC 1635`_, although it is common to use either the password
    "guest" or one's e-mail address for anonymous FTP,
    some FTP servers explicitly ask for the user's e-mail address
    and will not allow login with the "guest" password.

.. _RFC 1635: https://datatracker.ietf.org/doc/html/rfc1635

.. reqmeta:: ftp_user
.. setting:: FTP_USER

FTP_USER
--------

Default: ``"anonymous"``

The username to use for FTP connections when there is no ``"ftp_user"``
in ``Request`` meta.

.. setting:: GCS_PROJECT_ID

GCS_PROJECT_ID
-----------------

Default: ``None``

The Project ID that will be used when storing data on `Google Cloud Storage`_.

.. setting:: ITEM_PIPELINES

ITEM_PIPELINES
--------------

Default: ``{}``

A dict containing the item pipelines to use, and their orders. Order values are
arbitrary, but it is customary to define them in the 0-1000 range. Lower orders
process before higher orders.

Example:

.. code-block:: python

   ITEM_PIPELINES = {
       "mybot.pipelines.validate.ValidateMyItem": 300,
       "mybot.pipelines.validate.StoreMyItem": 800,
   }

.. setting:: ITEM_PIPELINES_BASE

ITEM_PIPELINES_BASE
-------------------

Default: ``{}``

A dict containing the pipelines enabled by default in Scrapy. You should never
modify this setting in your project, modify :setting:`ITEM_PIPELINES` instead.


.. setting:: JOBDIR

JOBDIR
------

Default: ``None``

A string indicating the directory for storing the state of a crawl when
:ref:`pausing and resuming crawls <topics-jobs>`.


.. setting:: LOG_ENABLED

LOG_ENABLED
-----------

Default: ``True``

Whether to enable logging.

.. setting:: LOG_ENCODING

LOG_ENCODING
------------

Default: ``'utf-8'``

The encoding to use for logging.

.. setting:: LOG_FILE

LOG_FILE
--------

Default: ``None``

File name to use for logging output. If ``None``, standard error will be used.

.. setting:: LOG_FILE_APPEND

LOG_FILE_APPEND
---------------

Default: ``True``

If ``False``, the log file specified with :setting:`LOG_FILE` will be
overwritten (discarding the output from previous runs, if any).

.. setting:: LOG_FORMAT

LOG_FORMAT
----------

Default: ``'%(asctime)s [%(name)s] %(levelname)s: %(message)s'``

String for formatting log messages. Refer to the
:ref:`Python logging documentation <logrecord-attributes>` for the whole
list of available placeholders.

.. setting:: LOG_DATEFORMAT

LOG_DATEFORMAT
--------------

Default: ``'%Y-%m-%d %H:%M:%S'``

String for formatting date/time, expansion of the ``%(asctime)s`` placeholder
in :setting:`LOG_FORMAT`. Refer to the
:ref:`Python datetime documentation <strftime-strptime-behavior>` for the
whole list of available directives.

.. setting:: LOG_FORMATTER

LOG_FORMATTER
-------------

Default: :class:`scrapy.logformatter.LogFormatter`

The class to use for :ref:`formatting log messages <custom-log-formats>` for different actions.

.. setting:: LOG_LEVEL

LOG_LEVEL
---------

Default: ``'DEBUG'``

Minimum level to log. Available levels are: CRITICAL, ERROR, WARNING,
INFO, DEBUG. For more info see :ref:`topics-logging`.

.. setting:: LOG_STDOUT

LOG_STDOUT
----------

Default: ``False``

If ``True``, all standard output (and error) of your process will be redirected
to the log. For example if you ``print('hello')`` it will appear in the Scrapy
log.

.. setting:: LOG_SHORT_NAMES

LOG_SHORT_NAMES
---------------

Default: ``False``

If ``True``, the logs will just contain the root path. If it is set to ``False``
then it displays the component responsible for the log output

.. setting:: LOG_VERSIONS

LOG_VERSIONS
------------

Default: ``["lxml", "libxml2", "cssselect", "parsel", "w3lib", "Twisted", "Python", "pyOpenSSL", "cryptography", "Platform"]``

Logs the installed versions of the specified items.

An item can be any installed Python package.

The following special items are also supported:

-   ``libxml2``

-   ``Platform`` (:func:`platform.platform`)

-   ``Python``

.. setting:: LOGSTATS_INTERVAL

LOGSTATS_INTERVAL
-----------------

Default: ``60.0``

The interval (in seconds) between each logging printout of the stats
by :class:`~scrapy.extensions.logstats.LogStats`.

.. setting:: MEMDEBUG_ENABLED

MEMDEBUG_ENABLED
----------------

Default: ``False``

Whether to enable memory debugging.

.. setting:: MEMDEBUG_NOTIFY

MEMDEBUG_NOTIFY
---------------

Default: ``[]``

When memory debugging is enabled a memory report will be sent to the specified
addresses if this setting is not empty, otherwise the report will be written to
the log.

Example::

    MEMDEBUG_NOTIFY = ['user@example.com']

.. setting:: MEMUSAGE_ENABLED

MEMUSAGE_ENABLED
----------------

Default: ``True``

Scope: ``scrapy.extensions.memusage``

Whether to enable the memory usage extension. This extension keeps track of
a peak memory used by the process (it writes it to stats). It can also
optionally shutdown the Scrapy process when it exceeds a memory limit
(see :setting:`MEMUSAGE_LIMIT_MB`), and notify by email when that happened
(see :setting:`MEMUSAGE_NOTIFY_MAIL`).

See :ref:`topics-extensions-ref-memusage`.

.. setting:: MEMUSAGE_LIMIT_MB

MEMUSAGE_LIMIT_MB
-----------------

Default: ``0``

Scope: ``scrapy.extensions.memusage``

The maximum amount of memory to allow (in megabytes) before shutting down
Scrapy  (if MEMUSAGE_ENABLED is True). If zero, no check will be performed.

See :ref:`topics-extensions-ref-memusage`.

.. setting:: MEMUSAGE_CHECK_INTERVAL_SECONDS

MEMUSAGE_CHECK_INTERVAL_SECONDS
-------------------------------

Default: ``60.0``

Scope: ``scrapy.extensions.memusage``

The :ref:`Memory usage extension <topics-extensions-ref-memusage>`
checks the current memory usage, versus the limits set by
:setting:`MEMUSAGE_LIMIT_MB` and :setting:`MEMUSAGE_WARNING_MB`,
at fixed time intervals.

This sets the length of these intervals, in seconds.

See :ref:`topics-extensions-ref-memusage`.

.. setting:: MEMUSAGE_NOTIFY_MAIL

MEMUSAGE_NOTIFY_MAIL
--------------------

Default: ``False``

Scope: ``scrapy.extensions.memusage``

A list of emails to notify if the memory limit has been reached.

Example::

    MEMUSAGE_NOTIFY_MAIL = ['user@example.com']

See :ref:`topics-extensions-ref-memusage`.

.. setting:: MEMUSAGE_WARNING_MB

MEMUSAGE_WARNING_MB
-------------------

Default: ``0``

Scope: ``scrapy.extensions.memusage``

The maximum amount of memory to allow (in megabytes) before sending a warning
email notifying about it. If zero, no warning will be produced.

.. setting:: NEWSPIDER_MODULE

NEWSPIDER_MODULE
----------------

Default: ``"<project name>.spiders"`` (:ref:`fallback <default-settings>`: ``""``)

Module where to create new spiders using the :command:`genspider` command.

Example::

    NEWSPIDER_MODULE = 'mybot.spiders_dev'

.. setting:: RANDOMIZE_DOWNLOAD_DELAY

RANDOMIZE_DOWNLOAD_DELAY
------------------------

Default: ``True``

If enabled, Scrapy will wait a random amount of time (between 0.5 * :setting:`DOWNLOAD_DELAY` and 1.5 * :setting:`DOWNLOAD_DELAY`) while fetching requests from the same
website.

This randomization decreases the chance of the crawler being detected (and
subsequently blocked) by sites which analyze requests looking for statistically
significant similarities in the time between their requests.

The randomization policy is the same used by `wget`_ ``--random-wait`` option.

If :setting:`DOWNLOAD_DELAY` is zero (default) this option has no effect.

.. _wget: https://www.gnu.org/software/wget/manual/wget.html

.. setting:: REACTOR_THREADPOOL_MAXSIZE

REACTOR_THREADPOOL_MAXSIZE
--------------------------

Default: ``10``

The maximum limit for Twisted Reactor thread pool size. This is common
multi-purpose thread pool used by various Scrapy components. Threaded
DNS Resolver, BlockingFeedStorage, S3FilesStore just to name a few. Increase
this value if you're experiencing problems with insufficient blocking IO.

.. setting:: REDIRECT_PRIORITY_ADJUST

REDIRECT_PRIORITY_ADJUST
------------------------

Default: ``+2``

Scope: ``scrapy.downloadermiddlewares.redirect.RedirectMiddleware``

Adjust redirect request priority relative to original request:

- **a positive priority adjust (default) means higher priority.**
- a negative priority adjust means lower priority.

.. setting:: ROBOTSTXT_OBEY

ROBOTSTXT_OBEY
--------------

Default: ``True`` (:ref:`fallback <default-settings>`: ``False``)

If enabled, Scrapy will respect robots.txt policies. For more information see
:ref:`topics-dlmw-robots`.

.. note::

    While the default value is ``False`` for historical reasons,
    this option is enabled by default in settings.py file generated
    by ``scrapy startproject`` command.

.. setting:: ROBOTSTXT_PARSER

ROBOTSTXT_PARSER
----------------

Default: ``'scrapy.robotstxt.ProtegoRobotParser'``

The parser backend to use for parsing ``robots.txt`` files. For more information see
:ref:`topics-dlmw-robots`.

.. setting:: ROBOTSTXT_USER_AGENT

ROBOTSTXT_USER_AGENT
^^^^^^^^^^^^^^^^^^^^

Default: ``None``

The user agent string to use for matching in the robots.txt file. If ``None``,
the User-Agent header you are sending with the request or the
:setting:`USER_AGENT` setting (in that order) will be used for determining
the user agent to use in the robots.txt file.

.. setting:: SCHEDULER

SCHEDULER
---------

Default: ``'scrapy.core.scheduler.Scheduler'``

The scheduler class to be used for crawling.
See the :ref:`topics-scheduler` topic for details.

.. setting:: SCHEDULER_DEBUG

SCHEDULER_DEBUG
---------------

Default: ``False``

Setting to ``True`` will log debug information about the requests scheduler.
This currently logs (only once) if the requests cannot be serialized to disk.
Stats counter (``scheduler/unserializable``) tracks the number of times this happens.

Example entry in logs::

    1956-01-31 00:00:00+0800 [scrapy.core.scheduler] ERROR: Unable to serialize request:
    <GET http://example.com> - reason: cannot serialize <Request at 0x9a7c7ec>
    (type Request)> - no more unserializable requests will be logged
    (see 'scheduler/unserializable' stats counter)


.. setting:: SCHEDULER_DISK_QUEUE

SCHEDULER_DISK_QUEUE
--------------------

Default: ``'scrapy.squeues.PickleLifoDiskQueue'``

Type of disk queue that will be used by the scheduler. Other available types
are ``scrapy.squeues.PickleFifoDiskQueue``,
``scrapy.squeues.MarshalFifoDiskQueue``,
``scrapy.squeues.MarshalLifoDiskQueue``.


.. setting:: SCHEDULER_MEMORY_QUEUE

SCHEDULER_MEMORY_QUEUE
----------------------

Default: ``'scrapy.squeues.LifoMemoryQueue'``

Type of in-memory queue used by the scheduler. Other available type is:
``scrapy.squeues.FifoMemoryQueue``.


.. setting:: SCHEDULER_PRIORITY_QUEUE

SCHEDULER_PRIORITY_QUEUE
------------------------

Default: ``'scrapy.pqueues.ScrapyPriorityQueue'``

Type of priority queue used by the scheduler. Another available type is
``scrapy.pqueues.DownloaderAwarePriorityQueue``.
``scrapy.pqueues.DownloaderAwarePriorityQueue`` works better than
``scrapy.pqueues.ScrapyPriorityQueue`` when you crawl many different
domains in parallel.


.. setting:: SCHEDULER_START_DISK_QUEUE

SCHEDULER_START_DISK_QUEUE
--------------------------

Default: ``'scrapy.squeues.PickleFifoDiskQueue'``

Type of disk queue (see :setting:`JOBDIR`) that the :ref:`scheduler
<topics-scheduler>` uses for :ref:`start requests <start-requests>`.

For available choices, see :setting:`SCHEDULER_DISK_QUEUE`.

.. queue-common-starts

Use ``None`` or ``""`` to disable these separate queues entirely, and instead
have start requests share the same queues as other requests.

.. note::

    Disabling separate start request queues makes :ref:`start request order
    <start-request-order>` unintuitive: start requests will be sent in order
    only until :setting:`CONCURRENT_REQUESTS` is reached, then remaining start
    requests will be sent in reverse order.

.. queue-common-ends


.. setting:: SCHEDULER_START_MEMORY_QUEUE

SCHEDULER_START_MEMORY_QUEUE
----------------------------

Default: ``'scrapy.squeues.FifoMemoryQueue'``

Type of in-memory queue that the :ref:`scheduler <topics-scheduler>` uses for
:ref:`start requests <start-requests>`.

For available choices, see :setting:`SCHEDULER_MEMORY_QUEUE`.

.. include:: settings.rst
    :start-after: queue-common-starts
    :end-before: queue-common-ends


.. setting:: SCRAPER_SLOT_MAX_ACTIVE_SIZE

SCRAPER_SLOT_MAX_ACTIVE_SIZE
----------------------------

.. versionadded:: 2.0

Default: ``5_000_000``

Soft limit (in bytes) for response data being processed.

While the sum of the sizes of all responses being processed is above this value,
Scrapy does not process new requests.

.. setting:: SPIDER_CONTRACTS

SPIDER_CONTRACTS
----------------

Default:: ``{}``

A dict containing the spider contracts enabled in your project, used for
testing spiders. For more info see :ref:`topics-contracts`.

.. setting:: SPIDER_CONTRACTS_BASE

SPIDER_CONTRACTS_BASE
---------------------

Default:

.. code-block:: python

    {
        "scrapy.contracts.default.UrlContract": 1,
        "scrapy.contracts.default.ReturnsContract": 2,
        "scrapy.contracts.default.ScrapesContract": 3,
    }

A dict containing the Scrapy contracts enabled by default in Scrapy. You should
never modify this setting in your project, modify :setting:`SPIDER_CONTRACTS`
instead. For more info see :ref:`topics-contracts`.

You can disable any of these contracts by assigning ``None`` to their class
path in :setting:`SPIDER_CONTRACTS`. E.g., to disable the built-in
``ScrapesContract``, place this in your ``settings.py``:

.. code-block:: python

    SPIDER_CONTRACTS = {
        "scrapy.contracts.default.ScrapesContract": None,
    }

.. setting:: SPIDER_LOADER_CLASS

SPIDER_LOADER_CLASS
-------------------

Default: ``'scrapy.spiderloader.SpiderLoader'``

The class that will be used for loading spiders, which must implement the
:ref:`topics-api-spiderloader`.

.. setting:: SPIDER_LOADER_WARN_ONLY

SPIDER_LOADER_WARN_ONLY
-----------------------

Default: ``False``

By default, when Scrapy tries to import spider classes from :setting:`SPIDER_MODULES`,
it will fail loudly if there is any ``ImportError`` or ``SyntaxError`` exception.
But you can choose to silence this exception and turn it into a simple
warning by setting ``SPIDER_LOADER_WARN_ONLY = True``.

.. setting:: SPIDER_MIDDLEWARES

SPIDER_MIDDLEWARES
------------------

Default:: ``{}``

A dict containing the spider middlewares enabled in your project, and their
orders. For more info see :ref:`topics-spider-middleware-setting`.

.. setting:: SPIDER_MIDDLEWARES_BASE

SPIDER_MIDDLEWARES_BASE
-----------------------

Default:

.. code-block:: python

    {
        "scrapy.spidermiddlewares.httperror.HttpErrorMiddleware": 50,
        "scrapy.spidermiddlewares.referer.RefererMiddleware": 700,
        "scrapy.spidermiddlewares.urllength.UrlLengthMiddleware": 800,
        "scrapy.spidermiddlewares.depth.DepthMiddleware": 900,
    }

A dict containing the spider middlewares enabled by default in Scrapy, and
their orders. Low orders are closer to the engine, high orders are closer to
the spider. For more info see :ref:`topics-spider-middleware-setting`.

.. setting:: SPIDER_MODULES

SPIDER_MODULES
--------------

Default: ``["<project name>.spiders"]`` (:ref:`fallback <default-settings>`: ``[]``)

A list of modules where Scrapy will look for spiders.

Example:

.. code-block:: python

    SPIDER_MODULES = ["mybot.spiders_prod", "mybot.spiders_dev"]

.. setting:: STATS_CLASS

STATS_CLASS
-----------

Default: ``'scrapy.statscollectors.MemoryStatsCollector'``

The class to use for collecting stats, who must implement the
:ref:`topics-api-stats`.

.. setting:: STATS_DUMP

STATS_DUMP
----------

Default: ``True``

Dump the :ref:`Scrapy stats <topics-stats>` (to the Scrapy log) once the spider
finishes.

For more info see: :ref:`topics-stats`.

.. setting:: STATSMAILER_RCPTS

STATSMAILER_RCPTS
-----------------

Default: ``[]`` (empty list)

Send Scrapy stats after spiders finish scraping. See
:class:`~scrapy.extensions.statsmailer.StatsMailer` for more info.

.. setting:: TELNETCONSOLE_ENABLED

TELNETCONSOLE_ENABLED
---------------------

Default: ``True``

A boolean which specifies if the :ref:`telnet console <topics-telnetconsole>`
will be enabled (provided its extension is also enabled).

.. setting:: TEMPLATES_DIR

TEMPLATES_DIR
-------------

Default: ``templates`` dir inside scrapy module

The directory where to look for templates when creating new projects with
:command:`startproject` command and new spiders with :command:`genspider`
command.

The project name must not conflict with the name of custom files or directories
in the ``project`` subdirectory.

.. setting:: TWISTED_REACTOR

TWISTED_REACTOR
---------------

.. versionadded:: 2.0

Default: ``"twisted.internet.asyncioreactor.AsyncioSelectorReactor"``

Import path of a given :mod:`~twisted.internet.reactor`.

Scrapy will install this reactor if no other reactor is installed yet, such as
when the ``scrapy`` CLI program is invoked or when using the
:class:`~scrapy.crawler.AsyncCrawlerProcess` class or the
:class:`~scrapy.crawler.CrawlerProcess` class.

If you are using the :class:`~scrapy.crawler.AsyncCrawlerRunner` class or the
:class:`~scrapy.crawler.CrawlerRunner` class, you also
need to install the correct reactor manually. You can do that using
:func:`~scrapy.utils.reactor.install_reactor`:

.. autofunction:: scrapy.utils.reactor.install_reactor

If a reactor is already installed,
:func:`~scrapy.utils.reactor.install_reactor` has no effect.

:class:`~scrapy.crawler.AsyncCrawlerRunner` and other similar classes raise an
exception if the installed reactor does not match the
:setting:`TWISTED_REACTOR` setting; therefore, having top-level
:mod:`~twisted.internet.reactor` imports in project files and imported
third-party libraries will make Scrapy raise an exception when it checks which
reactor is installed.

In order to use the reactor installed by Scrapy:

.. skip: next
.. code-block:: python

    import scrapy
    from twisted.internet import reactor


    class QuotesSpider(scrapy.Spider):
        name = "quotes"

        def __init__(self, *args, **kwargs):
            self.timeout = int(kwargs.pop("timeout", "60"))
            super(QuotesSpider, self).__init__(*args, **kwargs)

        async def start(self):
            reactor.callLater(self.timeout, self.stop)

            urls = ["https://quotes.toscrape.com/page/1"]
            for url in urls:
                yield scrapy.Request(url=url, callback=self.parse)

        def parse(self, response):
            for quote in response.css("div.quote"):
                yield {"text": quote.css("span.text::text").get()}

        def stop(self):
            self.crawler.engine.close_spider(self, "timeout")


which raises an exception, becomes:

.. code-block:: python

    import scrapy


    class QuotesSpider(scrapy.Spider):
        name = "quotes"

        def __init__(self, *args, **kwargs):
            self.timeout = int(kwargs.pop("timeout", "60"))
            super(QuotesSpider, self).__init__(*args, **kwargs)

        async def start(self):
            from twisted.internet import reactor

            reactor.callLater(self.timeout, self.stop)

            urls = ["https://quotes.toscrape.com/page/1"]
            for url in urls:
                yield scrapy.Request(url=url, callback=self.parse)

        def parse(self, response):
            for quote in response.css("div.quote"):
                yield {"text": quote.css("span.text::text").get()}

        def stop(self):
            self.crawler.engine.close_spider(self, "timeout")


If this setting is set ``None``, Scrapy will use the existing reactor if one is
already installed, or install the default reactor defined by Twisted for the
current platform.

.. versionchanged:: 2.7
   The :command:`startproject` command now sets this setting to
   ``twisted.internet.asyncioreactor.AsyncioSelectorReactor`` in the generated
   ``settings.py`` file.

.. versionchanged:: 2.13
   The default value was changed from ``None`` to
   ``"twisted.internet.asyncioreactor.AsyncioSelectorReactor"``.

For additional information, see :doc:`core/howto/choosing-reactor`.


.. setting:: URLLENGTH_LIMIT

URLLENGTH_LIMIT
---------------

Default: ``2083``

Scope: ``spidermiddlewares.urllength``

The maximum URL length to allow for crawled URLs.

This setting can act as a stopping condition in case of URLs of ever-increasing
length, which may be caused for example by a programming error either in the
target server or in your code. See also :setting:`REDIRECT_MAX_TIMES` and
:setting:`DEPTH_LIMIT`.

Use ``0`` to allow URLs of any length.

The default value is copied from the `Microsoft Internet Explorer maximum URL
length`_, even though this setting exists for different reasons.

.. _Microsoft Internet Explorer maximum URL length: https://support.microsoft.com/en-us/topic/maximum-url-length-is-2-083-characters-in-internet-explorer-174e7c8a-6666-f4e0-6fd6-908b53c12246

.. setting:: USER_AGENT

USER_AGENT
----------

Default: ``"Scrapy/VERSION (+https://scrapy.org)"``

The default User-Agent to use when crawling, unless overridden. This user agent is
also used by :class:`~scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware`
if :setting:`ROBOTSTXT_USER_AGENT` setting is ``None`` and
there is no overriding User-Agent header specified for the request.

.. setting:: WARN_ON_GENERATOR_RETURN_VALUE

WARN_ON_GENERATOR_RETURN_VALUE
------------------------------

Default: ``True``

When enabled, Scrapy will warn if generator-based callback methods (like
``parse``) contain return statements with non-``None`` values. This helps detect
potential mistakes in spider development.

Disable this setting to prevent syntax errors that may occur when dynamically
modifying generator function source code during runtime, skip AST parsing of
callback functions, or improve performance in auto-reloading development
environments.

Settings documented elsewhere:
------------------------------

The following settings are documented elsewhere, please check each specific
case to see how to enable and use them.

.. settingslist::

.. _Amazon web services: https://aws.amazon.com/
.. _breadth-first order: https://en.wikipedia.org/wiki/Breadth-first_search
.. _depth-first order: https://en.wikipedia.org/wiki/Depth-first_search
.. _Google Cloud Storage: https://cloud.google.com/storage/
