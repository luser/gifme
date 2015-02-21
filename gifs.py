#!/usr/bin/env python

import feedparser
import io
import multiprocessing
import multiprocessing.queues
import os
import Queue
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

def find_gifs_thread(q):
    '''
    Wait for results from find_gifs_process on the Queue |q| and
    add them to the singleton GifManager.
    '''
    while True:
        data = q.get()
        print 'Got URL %s' % data[0]
        gif_manager.add(data)

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


def find_gifs_rss():
    # TODO: use if-modified-since
    d = feedparser.parse('http://imgur.com/r/gifs/rss')
    for e in d.entries:
        for mc in e.get('media_content', []):
            if mc['type'] == 'image/gif':
                yield mc['url']

def find_gifs_process(q):
    '''
    Find GIFs from wherever. Put tuples of (url, duration in milliseconds)
    into the Queue |q|.
    '''
    # TODO: poll RSS feed
    s = set()
    while True:
        for gif in find_gifs_rss():
            if gif in s:
                continue
            print 'Found new gif: %s' % gif
            s.add(gif)
            duration = get_gif_duration(gif)
            if duration != 0:
                q.put((gif, duration))
        time.sleep(10)

def find_gifs():
    '''
    Kick off a Process to find GIFs, and a Thread to watch a Queue for
    results and stick them into the singleton GifManager.
    '''
    q = multiprocessing.queues.SimpleQueue()
    p = multiprocessing.Process(target=find_gifs_process, args=(q,))
    p.daemon = True
    p.start()
    t = threading.Thread(target=find_gifs_thread, args=(q,))
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
