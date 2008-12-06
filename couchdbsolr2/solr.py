# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# Apache Solr for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# A simple Solr client for python.
#
# quick examples on use:
#
# from solr import *
# c = SolrConnection(uri='http://localhost:8983/solr')
# c.add(id='500',name='python test doc')
# c.delete('123')
# c.commit()
# print c.search(q='id:[* TO *]', wt='python', rows='10',indent='on')
# data = c.search(q='id:500', wt='python')
# print 'first match=', eval(data)['response']['docs'][0]

import httplib2, logging, socket, urllib
from xml.sax.saxutils import escape

try:
    import cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

__all__ = ['SolrConnection']


class SolrConnection(object):

  def __init__(self, uri='http://localhost:8983/solr', postHeaders={}):
    self.uri = uri
    self.conn = httplib2.Http()
    self.xmlheaders = {'Content-Type': 'application/xml; charset=utf-8'}
    self.xmlheaders.update(postHeaders)
    self.formheaders = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}

  def __str__(self):
    return 'SolrConnection{uri=%s, postHeaders=%s}' % (self.uri, self.xmlheaders)

  def doPost(self,url,body,headers):
    try:
      response, content = self.conn.request(url, 'POST', body, headers)
      if response.status != 200:
        log.error("HTTP request returned code %d" % response.status)
        return None
    except httplib2.HttpLib2Error:
      log.exception("HTTP error")
      return None
    return content

  def doUpdateXML(self, request):
    data = self.doPost(self.uri + '/update', request, self.xmlheaders)
    if data is None:
      return None
    response = ET.fromstring(data)
    for lst in response.findall('./lst'):
      if lst.get('name') == 'responseHeader':
        for lst_int in lst.findall('./int'):
          if lst_int.get('name') == 'status':
            solr_status = int(lst_int.text)
            if solr_status != 0:
              raise SolrException(rsp.status, solr_status)
            break
        break
    return data

  def escapeVal(self,val):
    return escape(unicode(val))

  def escapeKey(self,key):
    return escape(unicode(key), {'"' : '&quot;'})

  def delete(self, id):
    xstr = '<delete><id>' + self.escapeVal(id) + '</id></delete>'
    return self.doUpdateXML(xstr)

  def deleteByQuery(self, query):
    xstr = '<delete><query>'+self.escapeVal(query)+'</query></delete>'
    return self.doUpdateXML(xstr)

  def __add(self, lst, fields):
    lst.append('<doc>')
    for f,v in fields.items():
      lst.append('<field name="')
      lst.append(self.escapeKey(str(f)))
      lst.append('">')
      lst.append(self.escapeVal(str(v)))
      lst.append('</field>')
    lst.append('</doc>')

  def add(self, **fields):
    lst=['<add>']
    self.__add(lst,fields)
    lst.append('</add>')
    xstr = ''.join(lst)
    return self.doUpdateXML(xstr)

  def addMany(self, arrOfMap):
    lst=['<add>']
    for doc in arrOfMap:
      self.__add(lst,doc)
    lst.append('</add>')
    xstr = ''.join(lst)
    return self.doUpdateXML(xstr)

  def commit(self, waitFlush=True, waitSearcher=True, optimize=False):
    xstr = '<commit'
    if optimize: xstr='<optimize'
    xstr += ' waitFlush="' + ('true' if waitFlush else 'false') + '"'
    xstr += ' waitSearcher="' + ('true' if waitSearcher else 'false') + '"'
    xstr += '/>'
    return self.doUpdateXML(xstr)

  def search(self, **params):
    request=urllib.urlencode(params, doseq=True)
    content = self.doPost(self.uri + '/select', request, self.formheaders)
    return content
