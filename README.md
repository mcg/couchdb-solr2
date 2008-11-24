CouchDB-Solr2
=============

CouchDB-Solr2 provides full-text indexing and full-text search to CouchDB
using Solr. It has a distributed architecture. Update notifications from
CouchDB are initially sent to an AMQP message queue. An intermediate server
reads from the message queue and updates Solr.

Dependencies
------------

[setuptools][setuptools]

CouchDB (with _external interface)

[Solr 1.3.x][solr]

AMQP broker

Installation
------------

The entire installation process is not going to be covered here so a
general outline will have to suffice.

First install a version of CouchDB with the _external interface.
This code was tested using @jchris's [Action2 branch][action2].

[Install Solr](http://wiki.apache.org/solr/SolrInstall), then copy the
`schema.xml` file from this distribution to the `conf` directory in your Solr
home. CouchDB-Solr2 only makes Solr commits when a document is deleted. You
will need to, at the least, uncomment the autoCommit section in
`solrconfig.xml`. For example:

  <autoCommit> 
    <maxDocs>10000</maxDocs>
    <maxTime>30000</maxTime> 
  </autoCommit>

Install an AMQP message broker. This code was tested with [RabbitMQ][rabbitmq].

Ensure that you have setuptools and then install CouchDB-Solr2. This is best
done using the command:

  # python setup.py develop

There are two INI files in the distribution which configure the CouchDB-Solr2
AMQP clients. Copy these to somewhere permanent and edit if necessary.

CouchDB-Solr2 has three commands:

1. couchdb-solr2-index
1. couchdb-solr2-query
1. couchdb-solr2-update

Observe where these are installed by the setup script.

Edit the `etc/couchdb/local.ini` file in your CouchDB install directory. Add
the following lines:

  [update_notification]
  solr_indexer=/path/to/couchdb-solr2-index -a /path/to/couchdb-solr2-index.ini

  [external]
  fti={"/path/to/couchdb-solr2-query", 1}

Start your servlet container and AMQP broker if you haven't already and then
CouchDB. Finally run `couchdb-solr2-update`:

  # /path/to/couchdb-solr2-update -a /path/to/couchdb-solr2-update.ini

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

The query parameters currently supported are

1. q
1. fq
1. fl
1. type
1. count
1. offset

`q`, `fq`, and `fl` are [standard Solr query parameters][solr-parameters]. `count` and `offset` are respectively equivalent
to the `rows` and `start` Solr parameters. `type` is used to match the `type`
CouchDB field described above. It is implemented as a filter query for
efficiency.

An example CouchDB document:

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
`post/title` and `post/content`. For every document indexed, a default field
called `_text` is available. `_text` allows searching on all CouchDB document
fields that were indexed.

Some example queries:

  http://127.0.0.1:5984/database/_external/fti?q=post/title:quick
  http://127.0.0.1:5984/database/_external/fti?q=post/content:search&count=5
  http://127.0.0.1:5984/database/_external/fti?type=Post

Thanks
------

A nod to @janl for suggesting I take another look at couchdb-solr and
couchdb-lucene when I started working on FTI. And, of course, many thanks
to @davisp whose code served as inspiration (and a source for a little
shameless stealing).


[setuptools]: http://peak.telecommunity.com/DevCenter/setuptools
[solr]: http://lucene.apache.org/solr/
[solr-parameters]: http://wiki.apache.org/solr/CommonQueryParameters
[action2]: http://github.com/jchris/couchdb/tree/action2
