#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flask
import redis
import hashlib
import os
import sys
import alfmin
import configparser
import markdown

# replace with send img!!!!
import base64

alfPath = os.path.dirname(os.path.realpath(__file__))
alfmin.alfPath = alfPath

# -----------------------------------------------------
# read config 
# -----------------------------------------------------


alfConfig = configparser.ConfigParser()
alfConfigFilePath = os.path.join( alfPath,'alf.conf')
if not os.path.exists(alfConfigFilePath):
    print('ALF config File not found! EXIT!')
    sys.exit(1)
alfConfig.read(alfConfigFilePath)
if not 'ALF' in alfConfig:
    print('please check configfile')
    sys.exit(1)
if 'admin' not in alfConfig['ALF'] or 'password' not in alfConfig['ALF']:
    print('please check configfile')
    sys.exit(1)

alfAdminName = alfConfig['ALF']['admin']
alfAdminPassword = alfConfig['ALF']['password']


# -----------------------------------------------------
# redis 
# -----------------------------------------------------


r = redis.Redis(charset="utf-8", decode_responses=True, db=5)
alfmin.r = r



# -----------------------------------------------------
# flask
# -----------------------------------------------------


app = flask.Flask(__name__)

app.secret_key = os.urandom(24)
app.permanent_session_lifetime = 600

# -----------------------------------------------------


@app.route('/stats', strict_slashes=False, methods=['GET', 'POST'])
def stats():
    if 'username' in flask.session:
        userName = flask.escape(flask.session['username'])
        if userName == 'admin':
            return flask.redirect(flask.url_for('admin'))
        if flask.request.method == "POST":
            a = dict(flask.request.form)
            alfData = { x : a[x][0] for x in a.keys() }
            # print(alfData)
            if set(('addAlfAlbum', 'bandName','albumName','albumInfo','downloadLimit')).issubset(alfData) and 'albumZip' in flask.request.files and 'albumImage' in flask.request.files:
                bandName = alfData['bandName']
                albumName = alfData['albumName']
                albumInfo = alfData['albumInfo']
                albumID = alfData['albumID']
                downloadLimit = alfData['downloadLimit']
                zipFile = flask.request.files['albumZip']
                imageFile = flask.request.files['albumImage']
                if '' in [zipFile.filename, imageFile.filename, bandName, albumName, albumInfo, albumID, downloadLimit]:
                    flask.flash('fill every field and select a zip-file')
                addAlbumSuccess, msg = alfmin.addAlfAlbum(albumID, bandName, albumName, userName, downloadLimit, albumInfo, imageFile, zipFile)
                flask.flash(msg)
            elif set(('addAlfCodes', 'albumName', 'numberOfCodes')).issubset(alfData):
                # print('generating ' + alfData['numberOfCodes'] + ' new codes for ' + alfData['albumName'])
                if alfData['numberOfCodes'].isdigit():
                    alfmin.createCodes(alfData['albumName'], userName ,int(alfData['numberOfCodes']))
                else:
                    flask.flash('number of codes is was not a number')
            else:
                flask.flash('invalid post request :(')
        releases = alfmin.listAlfUserAlbums(userName)
        return flask.render_template("stats.html", releases=releases)
    return 'You are not logged in <br><a href="' + flask.url_for('login') + '">login</a>'


@app.route('/stats/<albumID>/<codeFile>')
def downloadCodeFile(albumID, codeFile):
    if 'username' in flask.session:
        userName = flask.escape(flask.session['username'])
        if userName == 'admin':
            return flask.redirect(flask.url_for('admin'))
        codeFilePath = os.path.join( alfPath, 'users' , userName, albumID, codeFile )
        if os.path.exists(codeFilePath):
            return flask.send_file(codeFilePath, mimetype="text/plain", as_attachment=True, attachment_filename=codeFile)
    else:
        return flask.redirect(flask.url_for('login'))


@app.route('/admin', strict_slashes=False, methods=["GET", "POST"])
def admin():
    print('alfmin access')
    if 'username' in flask.session:
        userName = flask.escape(flask.session['username'])
        if userName == alfAdminName:
            if flask.request.method == 'POST':
                # convert ImmutableDict to dict and get rid of Lists
                a = dict(flask.request.form)
                alfData = { x : a[x][0] for x in a.keys() }
                if 'alfaction' in alfData:
                    alfAction = alfData.pop('alfaction')
                    if alfAction == 'addAlfUser' and 'password1' in alfData and 'password2' in alfData and 'username' in alfData:
                        user = alfData['username']
                        if alfData['password1'] == alfData['password2']:
                            passwd = alfData['password1']
                            addAlfUserSuccess = alfmin.addAlfUser( user, passwd)
                            if addAlfUserSuccess:
                                flask.flash("user "+user+" added!")
                            else:
                                flask.flash("user "+user+" not added, please recheck input")
                        else:
                            flask.flash("user "+user+" not added, please recheck input")
                    elif alfAction == 'deleteAlfUser' and 'username' in alfData:
                            user = alfData['username']
                            print(user)
                            deleteAlfUserSuccess = alfmin.deleteAlfUser(user)
                            if deleteAlfUserSuccess:
                                flask.flash("user "+user+" deleted")
                            else:
                                flask.flash("user "+user+" not deleted :(")
                    else:
                        flask.flash("something went wrong :(")
            users = alfmin.listAlfUsers()
            return flask.render_template("admin.html", users=users)
        return flask.redirect(flask.url_for('stats'))
    return flask.redirect(flask.url_for('login'))


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
        elif userName == alfAdminName and flask.request.form['password'] == alfAdminPassword:
            flask.session.permanent = True
            flask.session['username'] = userName
            return flask.redirect(flask.url_for('admin'))
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
            albumText = markdown.markdown(albumText)
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
    #app.run(host='localhost', port=64004, debug=True)



