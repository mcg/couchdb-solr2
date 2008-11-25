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


# $Id$
# A simple Solr client for python.
# This is prototype level code and subject to change.
#
# quick examples on use:
#
# from solr import *
# c = SolrConnection(host='localhost:8983', persistent=True)
# c.add(id='500',name='python test doc')
# c.delete('123')
# c.commit()
# print c.search(q='id:[* TO *]', wt='python', rows='10',indent='on')
# data = c.search(q='id:500', wt='python')
# print 'first match=', eval(data)['response']['docs'][0]

import httplib
import socket
import urllib
from xml.sax.saxutils import escape

try:
    import cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


class SolrException(Exception):
  def __init__(self, httpcode, appcode=None, reason=None, body=None):
    self.httpcode,self.appcode,self.reason,self.body = httpcode,appcode,reason,body
  def __str__(self):
    return 'HTTP code=%s, Application code=%s, Reason=%s, body=%s' % (self.httpcode,self.appcode,self.reason,self.body)


class SolrConnection(object):
  def __init__(self, host='localhost:8983', solrBase='/solr', persistent=True, postHeaders={}):
    self.host = host
    self.solrBase = solrBase
    self.persistent = persistent
    self.reconnects = 0
    #a real connection to the server is not opened at this point.
    self.conn = httplib.HTTPConnection(self.host)
    #self.conn.set_debuglevel(1000000)
    self.xmlheaders = {'Content-Type': 'application/xml; charset=utf-8'}
    self.xmlheaders.update(postHeaders)
    if not self.persistent: self.xmlheaders['Connection']='close'
    self.formheaders = {'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'}
    if not self.persistent: self.formheaders['Connection']='close'

  def __str__(self):
    return 'SolrConnection{host=%s, solrBase=%s, persistent=%s, postHeaders=%s, reconnects=%s}' % \
        (self.host, self.solrBase, self.persistent, self.xmlheaders, self.reconnects)

  def __reconnect(self):
    self.reconnects+=1
    self.conn.close()
    self.conn.connect()

  def __errcheck(self,rsp):
    if rsp.status != 200:
      ex = SolrException(rsp.status)
      try:
        ex.body = rsp.read()
      except:
        pass
      raise ex
    return rsp

  def doPost(self,url,body,headers):
    try:
      self.conn.request('POST', url, body, headers)
      return self.__errcheck(self.conn.getresponse())
    except (socket.error,httplib.CannotSendRequest) :
      #Reconnect in case the connection was broken from the server going down,
      #the server timing out our persistent connection, or another
      #network failure. Also catch httplib.CannotSendRequest because the
      #HTTPConnection object can get in a bad state.
      self.__reconnect()
      self.conn.request('POST', url, body, headers)
      return self.__errcheck(self.conn.getresponse())

  def doUpdateXML(self, request):
    try:
      rsp = self.doPost(self.solrBase+'/update', request, self.xmlheaders)
      data = rsp.read()
    finally:
      if not self.persistent: self.conn.close()

    # Kind of lame until we get decent XPath in ElementTree 1.3
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
    xstr = '<delete><id>'+self.escapeVal(`id`)+'</id></delete>'
    return self.doUpdateXML(xstr)

  def deleteByQyery(self, query):
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
    if not waitSearcher:  #just handle deviations from the default
      if not waitFlush: xstr +=' waitFlush="false" waitSearcher="false"'
      else: xstr += ' waitSearcher="false"'
    xstr += '/>'
    return self.doUpdateXML(xstr)

  def search(self, **params):
    request=urllib.urlencode(params, doseq=True)
    try:
      rsp = self.doPost(self.solrBase+'/select', request, self.formheaders)
      data = rsp.read()
    finally:
      if not self.persistent: self.conn.close()
    return data
