#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flask
import redis
import hashlib
import os
import base64

r = redis.Redis(charset="utf-8", decode_responses=True, db=5)

alfPath = os.path.dirname(os.path.realpath(__file__))

app = flask.Flask(__name__)

app.secret_key = os.urandom(24)
app.permanent_session_lifetime = 600




def getAlbumStats(albumRedisKey, userName):
    '''
    Returns a triple of stats:
    (used Codes , total Downloads incl. multiple , number of codes)
    '''
    album = r.hgetall(albumRedisKey)
    uniqueStats = 0
    totalStats = 0
    numberOfCodes = 0
    if 'user' in album:
        if userName == album['user']:
            for code in album:
                if code not in ['stats', 'limit', 'user' ,'bandname', 'albumname','damniam']:
                    numberOfCodes += 1
                    dlCount= int(album[code]) 
                    totalStats += dlCount
                    if dlCount > 0:
                        uniqueStats += 1
    return uniqueStats, totalStats, numberOfCodes


@app.route('/stats', strict_slashes=False)
def stats():
    if 'username' in flask.session:
        userName =  flask.escape(flask.session['username']) 
        releases = r.hgetall('USER:' + userName)
        releases.pop('password')
        for release in releases:
            albumImageFile = alfPath + '/users/' + userName + '/' + release + '/' + release + '.jpg'
            albumImage = 'data:image/jpg;base64,' + base64.b64encode( open(albumImageFile, 'rb').read() ).decode('utf-8')
            uniqueStats, totalStats, numberOfCodes = getAlbumStats('ALBUM:' + release,userName)
            releases[release] = {
                                'uniqueStats': uniqueStats,
                                'totalStats': totalStats,
                                'numberOfCodes': numberOfCodes,
                                'albumImage': albumImage,
                                'bandName': r.hget('ALBUM:' + release, 'bandname'),
                                'albumName': r.hget('ALBUM:' + release, 'albumname')
                                }
            
        return flask.render_template("stats.html", releases=releases)
    return 'You are not logged in <br><a href="' + flask.url_for('login') + '">login</a>'



@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'POST':
        userName = flask.request.form['username']
        passwordHash = hashlib.sha1( flask.request.form['password'].encode('utf-8') ).hexdigest()
        if "USER:" + userName in r.keys():
            if passwordHash == r.hget('USER:' + userName, 'password'): 
                flask.session.permanent = True
                flask.session['username'] = userName
                return flask.redirect(flask.url_for('stats'))
    return '''
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
    '''


@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    flask.session.pop('username', None)
    return flask.redirect(flask.url_for('stats'))



@app.errorhandler(404)
def page_not_found(e):
    return 'Welcome to ALF'


@app.route('/')
def index():
    return 'Welcome to ALF'


@app.route("/<handleThis>", defaults={'code': None}, strict_slashes=False)
@app.route("/<handleThis>/<code>")
def handler(handleThis, code=None):
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
                if int(maxDownloads) > int(downloadCount):
                    downloadCount += 1
                    r.hset(redisKey, hashed, downloadCount)
                    zipFile = alfPath + '/users/' + userName + '/' + handleThis + '/' + handleThis + '.zip'
                    return flask.send_file(zipFile, mimetype="application/zip", as_attachment=True, attachment_filename=str(bandName) + ' - ' + str(albumName) + '.zip')
                else:
                    return '<script>alert("Invalid Code");window.location.replace("../' + str(handleThis)  + '")</script>'


if __name__ == '__main__':
    app.run(host='localhost', port=64004)



