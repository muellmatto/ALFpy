#!/usr/bin/env python3

import flask
import redis
import hashlib
import os
import base64

# r = redis.Redis(unix_socket_path='/home/damniam/.redis/sock', db=4)
r = redis.Redis(charset="utf-8", decode_responses=True)

alfPath = os.path.dirname(os.path.realpath(__file__))

app = flask.Flask(__name__)


@app.errorhandler(404)
def page_not_found(e):
    return 'Welcome to ALF'

@app.route('/')
def index():
    return 'Welcome to ALF'

@app.route("/<handleThis>", defaults={'code': None}, strict_slashes=False)
@app.route("/<handleThis>/<code>")
def handler(handleThis, code=None):
    print( flask.request )
    # check if album
    redisKey = "ALBUM:" + str(handleThis)
    if r.hget(redisKey, 'bandname') == None:
        return 'Welcome to ALF'
    else:
        bandName = r.hget(redisKey, 'bandname')
        albumName = r.hget(redisKey, 'albumname')
        userName = r.hget(redisKey, 'user')
        # check if code empty - display downloadpage
        if code == None:
            albumImageFile = alfPath + '/users/' + userName + '/' + handleThis + '/' + handleThis + '.jpg'
            albumImage = 'data:image/jpg;base64,' + base64.b64encode( open(albumImageFile, 'rb').read() ).decode('utf-8')
            albumText = open(alfPath + '/users/' + userName + '/' + handleThis + '/' + handleThis + '.html' , 'r').read()
            return flask.render_template("download.html", bandName=bandName, albumName=albumName, infoText=albumText, albumImage=albumImage) 
        else:
            # check for code and start download
            hashed = hashlib.sha1(code.encode('utf-8')).hexdigest()
            if r.hget(redisKey, hashed) == None:
                return '<script>alert("Invalid Code");window.location.replace("../' + str(handleThis)  + '")</script>'
            else:
                maxDownloads = int(r.hget(redisKey, "limit"))
                downloadCount = int(r.hget(redisKey, hashed))
                stats = int(r.hget(redisKey, "stats"))
                if int(maxDownloads) > int(downloadCount):
                    downloadCount += 1
                    stats += 1
                    r.hset(redisKey, hashed, downloadCount)
                    r.hset(redisKey, "stats", stats)
                    zipFile = alfPath + '/users/' + userName + '/' + handleThis + '/' + handleThis + '.zip'
                    return flask.send_file(zipFile, mimetype="application/zip", as_attachment=True, attachment_filename=str(bandName) + ' - ' + str(albumName) + '.zip')
                else:
                    return '<script>alert("Invalid Code");window.location.replace("../' + str(handleThis)  + '")</script>'


app.run(host='localhost', port=64004)





