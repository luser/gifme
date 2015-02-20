#!/usr/bin/env python

import json
import web

from gifs import find_gifs, gif_manager

urls = (
    '/', 'root',
    '/feed', 'feed',
)

app = web.application(urls, globals())
wsgiapp = app.wsgifunc()
render = web.template.render('templates/')

class root:
    def GET(self):
        return render.index()

class feed:
    def GET(self):
        web.header("Content-Type", "text/event-stream")
        # 2kb padding for IE
        yield ':' + ' ' * 2049 + '\n'
        last_id = int(web.ctx.env.get('HTTP_LAST_EVENT_ID', 0))
        with gif_manager.listen() as gifs:
            for data in gifs:
                print 'Got data: %s' % str(data)
                if data is None:
                    yield "event: ping\ndata: 1\n\n"
                else:
                    i, gif, duration = data
                    if i > last_id:
                        yield "event: gif\nid: %d\ndata: %s\n\n" % (i, json.dumps({'url': gif, 'duration': duration}))

if __name__ == "__main__":
    find_gifs()
    app.run()
