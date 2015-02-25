#!/usr/bin/env python

import feedparser
import io
import os
import Queue
import re
import requests
import struct
import threading
import time

from contextlib import contextmanager

class GifManager(object):
    def __init__(self):
        self._nextid = 1
        self._gifs = []
        self._queues = set()

    @contextmanager
    def listen(self):
        q = Queue.Queue()
        self._queues.add(q)
        def iter_gifs():
            for gif in self._gifs:
                yield gif
            while True:
                try:
                    data = q.get(True, 30)
                    yield data
                except Queue.Empty:
                    yield None
        try:
            yield iter_gifs()
        finally:
            self._queues.remove(q)

    def add(self, gif):
        # TODO: OrderedSet or something?
        data = (self._nextid,) + gif
        self._nextid += 1
        self._gifs.append(data)
        for q in self._queues:
            try:
                q.put_nowait(data)
            except Queue.Full:
                pass
# Singleton instance
gif_manager = GifManager()

def find_gifs_localfile():
    '''
    For testing, read the contents of /tmp/gifs.
    '''
    if not hasattr(find_gifs_localfile, 'last'):
        find_gifs_localfile.last = 0
    now = os.stat('/tmp/gifs').st_mtime
    if now > find_gifs_localfile.last:
        find_gifs_localfile.last = now
        for gif in open('/tmp/gifs', 'r').read().splitlines():
            gif = gif.strip()
            if not gif:
                continue
            yield gif


def fetch_if_modified(url, date):
    headers = {}
    if date:
        headers['If-Modified-Since'] = date
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.text, r.headers.get('date', None)
    elif r.status_code == 304:
        return None, r.headers.get('date', None)
    return None, None

def fixup_or_reject_url(url):
    if url.endswith('.gifv'):
        return url[:-1]
    if '/gallery/' in url:
        return None
    if 'imgur.com' in url and not url.endswith('.gif'):
        return url.replace('imgur.com', 'i.imgur.com') + '.gif'
    return url

def find_gifs_rss():
    # TODO: use if-modified-since
    d = feedparser.parse('http://imgur.com/r/gifs/rss')
    for e in d.entries:
        for mc in e.get('media_content', []):
            if mc['type'] == 'image/gif':
                yield mc['url']

def find_gifs_facebook_group(group_id, access_token):
    r = requests.get('https://graph.facebook.com/v2.2/{group_id}/feed?access_token={access_token}'.format(group_id=group_id, access_token=access_token))
    if r.status_code == 200:
        try:
            link_re = re.compile('(https?://[^\s]+)')
            for post in r.json()['data']:
                link = post.get('link', None)
                if link:
                    yield link
                message = post.get('message', None)
                if message:
                    match = link_re.search(message)
                    if match:
                        link = fixup_or_reject_url(match.group(0))
                        if link:
                            yield link
        except ValueError:
            return

def find_gifs_thread():
    '''
    Find GIFs from wherever. Add tuples of (url, duration in milliseconds)
    to the singleton GifManager
    '''
    s = set()
    while True:
        for gif in find_gifs_rss():
            if gif in s:
                continue
            print 'Found new gif: %s' % gif
            s.add(gif)
            duration = get_gif_duration(gif)
            if duration != 0:
                gif_manager.add((gif, duration))
        time.sleep(10)

def find_gifs():
    '''
    Kick off a Thread to find GIFs and stick them into the singleton GifManager.
    '''
    t = threading.Thread(target=find_gifs_thread)
    t.daemon = True
    t.start()


class GIFError(Exception): pass

def gif_duration(f):
    '''
    Given a file object |f|, parse the GIF file it contains and
    return the duration of the animation in milliseconds.

    Raises GIFError on malformed data.
    '''
    delay = 0
    # Check signature
    if f.read(6) not in ('GIF87a', 'GIF89a'):
        raise GIFError('not a valid GIF file')
    # Skip logical screen w/h
    f.seek(4, 1)
    def skip_color_table(flags):
        if flags & 0x80: f.seek(3 << ((flags & 7) + 1), 1)
    # Read flags to check presence of color table
    flags = ord(f.read(1))
    # Skip last 2 bytes of Logical Screen Descriptor
    f.seek(2, 1)
    skip_color_table(flags)
    while True:
        block = f.read(1)
        if block == ';': break
        if block == '!':
            if f.read(1) == '\xf9':
                # Graphic Control Extension
                size = f.read(1)
                if ord(size) != 4:
                    raise GIFError('Unknown Graphic Control Extension size')
                # Skip flags
                f.seek(1, 1)
                # Delay is in tenths of a second
                delay += struct.unpack('<H', f.read(2))[0] * 10
                # Skip Transparent Color Index
                f.seek(1, 1)
        elif block == ',':
            # Image Descriptor
            f.seek(8, 1)
            skip_color_table(ord(f.read(1)))
            f.seek(1, 1)
        else: raise GIFError('unknown block type')
        while True:
            l = ord(f.read(1))
            if not l: break
            f.seek(l, 1)
    return delay

def get_gif_duration(url):
    '''
    Return the duration of the animation of the GIF at |url|
    in milliseconds, or None on error.
    '''
    r = requests.get(url)
    if r.status_code != 200:
        return None
    try:
        duration = gif_duration(io.BytesIO(r.content))
    except GIFError:
        return None
    return duration
