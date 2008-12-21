CouchDB-Solr2
=============

CouchDB-Solr2 provides a distributed architecture for full-text indexing and
searching within CouchDB. Update notifications from CouchDB are initially sent
to an AMQP exchange. An intermediary server then listens on that exchange for
incoming AMQP messages and alerts Solr of the updates.

Dependencies
------------

* [setuptools][setuptools]
* [CouchDB][couchdb]
* [CouchDB Python][couchdb-python]
* [Solr 1.3.x][solr]
* AMQP broker (e.g. [RabbitMQ][rabbitmq])

Installation
------------

Details of the installation of all dependencies is not going to be covered
here, so hopefully a general outline will suffice.

CouchDB-Solr2 requires Python 2.5.x or greater.

CouchDB-Solr2 requires r727136 or newer of CouchDB (which has support for
external processes).

[Install Solr](http://wiki.apache.org/solr/SolrInstall), then copy the
`schema.xml` file from this distribution to the `conf` directory in your Solr
home.

CouchDB-Solr2 only makes Solr commits when a document or database is deleted.
You will need to, at the least, uncomment the autoCommit section in
`solrconfig.xml`. For example:

    <autoCommit> 
        <maxDocs>10000</maxDocs>
        <maxTime>30000</maxTime> 
    </autoCommit>

It should also be noted that CouchDB-Solr2 currently makes no attempt to
optimize the Solr index.

Next, install an AMQP message broker. CouchDB-Solr2 is tested with RabbitMQ.

Ensure that you have setuptools and then install CouchDB-Solr2.

    # python setup.py install

CouchDB-Solr2 has three commands:

1. `couchdb-solr2-index`
1. `couchdb-solr2-query`
1. `couchdb-solr2-update`

Observe where these are installed by the setup script.

There are two INI files in the distribution which are intended for use with
`couchdb-solr2-index` and `couchdb-solr2-update`. Copy these to a more
permanent location and edit if necessary.

Edit the `etc/couchdb/local.ini` file in your CouchDB install directory. Add
the following lines:

    [update_notification]
    solr_indexer = /path/to/couchdb-solr2-index -c /path/to/couchdb-solr2-index.ini

    [external]
    fti = /path/to/couchdb-solr2-query

    [httpd_db_handlers]
    _external = {couch_httpd_external, handle_external_req}


You can find additional options to these two commands by running them with
the `--help` option.

Then start your servlet container and AMQP broker if you haven't already.
After that start CouchDB. Finally you will run `couchdb-solr2-update`. E.g:

    # /path/to/couchdb-solr2-update -c /path/to/couchdb-solr2-update.ini

For convenience, there is a Debian init script in the `init.d` directory
for `couchdb-solr2-update`.

Usage
-----

Each CouchDB document that you want indexed needs two special fields:
`solr_fields` and `type`.

`solr_fields` must be a JSON array listing the names of fields within the
document that will be recursively processed and then indexed by Solr.

`type` is a string that identifies a document as belonging to a class of
similar documents.

A URI of the form `http://SERVER:5984/DATABASE/_external/fti` is used to
access full-text search.

The query interface supports arbitrary query parameters. There is built-in
support for the [standard Solr query parameters][solr-parameters] and the
following:

1. `count`
1. `offset`
1. `type`

`count` and `offset` are respectively equivalent to the `rows` and `start` Solr
parameters. `type` is used to match the `type` CouchDB field described above.

Arbitrary query parameter support allows for a number of fascinating
possibilities. For example, the author has combined CouchDB-Solr2 with
[LocalSolr][localsolr] to bring geographical searching capabilities to CouchDB.

Let's take a look at an example CouchDB document:

    {
        "_id": "uniqueid",
        "_rev": "1",
        "type" : "Post",
        "post" : {
            "title" : "A quick post",
            "content" : "This blog post can be searched",
        },
        "solr_fields" : ["post"]
    }

When this document is updated, the `post` field is recursively processed
by CouchDB-Solr2. Two Solr fields are dynamically generated:
`post/title` and `post/content`.

By default (configured in `schema.xml`) a default field called `_text` is
available for every indexed document. `_text` allows searching on all CouchDB
document fields that were made searchable.

Some example queries:

    http://127.0.0.1:5984/database/_external/fti?q=post/title:quick
    http://127.0.0.1:5984/database/_external/fti?q=post/content:search&count=5
    http://127.0.0.1:5984/database/_external/fti?type=Post

Credits
-------

Many of the concepts in [Paul Davis'][davisp] couchdb-lucene and couchdb-solr
projects served as inspiration for CouchDB-Solr2.


[setuptools]: http://peak.telecommunity.com/DevCenter/setuptools
[couchdb]: http://couchdb.apache.org/
[couchdb-python]: http://code.google.com/p/couchdb-python/
[solr]: http://lucene.apache.org/solr/
[rabbitmq]: http://www.rabbitmq.com/
[solr-parameters]: http://wiki.apache.org/solr/CommonQueryParameters
[localsolr]: http://sourceforge.net/projects/locallucene/
[davisp]: http://github.com/davisp
