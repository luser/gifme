#!/usr/bin/env python

import json
import web

urls = (
    '/', 'root',
    '/feed', 'feed',
)

app = web.application(urls, globals())
render = web.template.render('templates/')

# http://www.reddit.com/r/gifs/.rss
gifs = [
    'http://i.imgur.com/5eYrRsv.gif',
    'http://i.imgur.com/VgYTG9o.gif',
    'http://i.imgur.com/gzl3RBq.gif',
    'http://i.imgur.com/DatMoZd.gif',
]

class root:
    def GET(self):
        return render.index()

class feed:
    def GET(self):
        web.header("Content-Type", "text/event-stream")
        last_id = int(web.ctx.env.get('HTTP_LAST_EVENT_ID', 0))
        next_id = last_id+1 if last_id > len(gifs) else len(gifs)
        if last_id < len(gifs):
            for i, gif in enumerate(gifs[last_id:]):
                yield "event: gif\nid: %d\ndata: %s\n\n" % (i, json.dumps({'url': gif}))
        #TODO: wait for more gifs
        while True:
            time.sleep(10)
            yield "event: ping\nid: %d\ndata: 1\n\n" % next_id
            next_id += 1

if __name__ == "__main__":
    app.run()
