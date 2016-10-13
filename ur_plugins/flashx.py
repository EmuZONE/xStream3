"""
    Kodi urlresolver plugin
    Copyright (C) 2014  smokdpi
    Updated by Gujal (c) 2016

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import re
from urlresolver.plugins.lib import jsunpack
from urlresolver.plugins.lib import helpers
from urlresolver import common
from urlresolver.resolver import UrlResolver, ResolverError

class FlashxResolver(UrlResolver):
    name = "flashx"
    domains = ["flashx.tv"]
    pattern = '(?://|\.)(flashx\.tv)/(?:embed-|dl\?|embed.php\?c=)?([0-9a-zA-Z/-]+)'

    def __init__(self):
        self.net = common.Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {'User-Agent': common.FF_USER_AGENT}
        html = self.net.http_GET(web_url, headers=headers).content
        if 'File Not Found' in html:
            raise ResolverError('File got deleted?')
        cookies = self.__get_cookies(html)

        match = re.compile('\'([^\']+counter\.cgi[^\']+)\'', re.DOTALL).findall(html)

        if not match:
            raise ResolverError('Site structure changed!')

        self.net.http_GET(match[0], headers=headers)
        data = helpers.get_hidden(html)
        data['imhuman'] = 'Proceed to this video'
        common.kodi.sleep(5000)
        headers.update({'Referer': web_url, 'Cookie': '; '.join(cookies)})

        html = self.net.http_POST('http://www.flashx.tv/dl', data, headers=headers).content
        sources = []
        for match in re.finditer('(eval\(function.*?)</script>', html, re.DOTALL):
            packed_data = jsunpack.unpack(match.group(1))
            sources += self.__parse_sources_list(packed_data)
        print 'FXDe:'
        print html
        source = helpers.pick_source(sources, self.get_setting('auto_pick') == 'true')
        return source

    def __get_cookies(self, html):
        cookies = {'ref_url': 'http://www.flashx.tv/'}
        for match in re.finditer("\$\.cookie\(\s*'([^']+)'\s*,\s*'([^']+)", html):
            key, value = match.groups()
            cookies[key] = value
        return cookies

    def __parse_sources_list(self, html):
        sources = []
        match = re.search('sources\s*:\s*\[(.*?)\]', html, re.DOTALL)
        if match:
            for match in re.finditer('''['"]?file['"]?\s*:\s*['"]([^'"]+)['"][^}]*['"]?label['"]?\s*:\s*['"]([^'"]*)''', match.group(1), re.DOTALL):
                stream_url, label = match.groups()
                stream_url = stream_url.replace('\/', '/')
                sources.append((label, stream_url))
        return sources

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, 'http://{host}/{media_id}')

    @classmethod
    def get_settings_xml(cls):
        xml = super(cls, cls).get_settings_xml()
        xml.append('<setting id="%s_auto_pick" type="bool" label="Automatically pick best quality" default="false" visible="true"/>' % (cls.__name__))
        return xml