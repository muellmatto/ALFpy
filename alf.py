#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from functools import wraps
from hashlib import sha1
from os.path import dirname, exists, join, realpath
from sys import exit

import flask
from markdown import markdown

import alfmin

# replace with send img!!!!
import base64

alfPath = dirname(realpath(__file__))

# -----------------------------------------------------
# read config 
# -----------------------------------------------------

try:
    from config.config import (
            ALF_SECRET,
            ALF_ADMIN_NAME,
            ALF_ADMIN_PASSWORD
    )
except:
    print('please check config.py')
    exit(1)

alfAdminName = ALF_ADMIN_NAME
alfAdminPassword = ALF_ADMIN_PASSWORD


# -----------------------------------------------------
# flask
# -----------------------------------------------------


app = flask.Flask(__name__)

app.secret_key = ALF_SECRET
app.permanent_session_lifetime = 600

# -----------------------------------------------------

def alfSession(wrapped):
    @wraps(wrapped)
    def alfRequest(*args, **kwargs):
        if 'username' in flask.session:
            return wrapped(*args, **kwargs)
        else:
            # return flask.redirect(flask.url_for('login'))
            return 'You are not logged in <br><a href="' + flask.url_for('login') + '">login</a>'
    return alfRequest


@app.route('/stats', strict_slashes=False, methods=['GET', 'POST'])
@alfSession
def stats():
    userName = flask.escape(flask.session['username'])
    if userName == alfAdminName:
        return flask.redirect(flask.url_for('admin'))
    if flask.request.method == "POST":
        a = dict(flask.request.form)
        # alfData = { x : a[x][0] for x in a.keys() }   # a[x][0]  .. why???
        alfData = { x : a[x] for x in a.keys() }
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
            elif albumID in ['login','logout','stats','admin']:
                flask.flash('please choose a different id')
            else:
                addAlbumSuccess, msg = alfmin.addAlfAlbum(albumID, bandName, albumName, userName, downloadLimit, albumInfo, imageFile, zipFile)
                flask.flash(msg)
        elif set(('addAlfCodes', 'albumName', 'numberOfCodes')).issubset(alfData):
            if alfData['numberOfCodes'].isdigit():
                alfmin.createCodes(alfData['albumName'], userName ,int(alfData['numberOfCodes']))
            else:
                flask.flash('number of codes is was not a number')
        else:
            flask.flash('invalid post request :(')
    releases = alfmin.listAlfUserAlbums(userName)
    return flask.render_template("stats.html", releases=releases)


@app.route('/stats/<albumID>/<codeFile>')
@alfSession
def downloadCodeFile(albumID, codeFile):
    userName = flask.escape(flask.session['username'])
    if userName == alfAdminName:
        return flask.redirect(flask.url_for('admin'))
    codeFilePath = join( alfPath, 'users' , userName, albumID, codeFile )
    if exists(codeFilePath):
        return flask.send_file(codeFilePath, mimetype="text/plain", as_attachment=True, attachment_filename=codeFile)


@app.route('/admin', strict_slashes=False, methods=["GET", "POST"])
@alfSession
def admin():
        userName = flask.escape(flask.session['username'])
        if userName == alfAdminName:
            if flask.request.method == 'POST':
                # convert ImmutableDict to dict and get rid of Lists
                a = dict(flask.request.form)
                alfData = { x : a[x] for x in a.keys() }
                # alfData = { x : a[x][0] for x in a.keys() }  # a[x][0] WHY??
                if 'alfaction' in alfData:
                    alfAction = alfData.pop('alfaction')
                    if alfAction == 'addAlfUser' and 'password1' in alfData and 'password2' in alfData and 'username' in alfData:
                        user = alfData['username']
                        if user == alfAdminName:
                            flask.flash('username cannot be the same as adminname')
                        else:
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
                            print('deleted user: '.format(user))
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

@app.route('/login', methods=['GET', 'POST'])
@alfmin.db_session
def login():
    if flask.request.method == 'POST':
        userName = flask.request.form['username']
        passwordHash = sha1( flask.request.form['password'].encode('utf-8') ).hexdigest()
        user = alfmin.User.get(name=userName, password_hash=passwordHash)
        if user:
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

@app.route("/<album_id>", defaults={'code': None}, strict_slashes=False)
@app.route("/<album_id>/<code>")
@alfmin.db_session
def handler(album_id, code=None):
    album = alfmin.Album.get(album_id=album_id)
    # check if album
    if album is None:
        return 'Welcome to ALF'
    # check if code == empty - display downloadpage
    if code == None:
        albumImageFile = alfPath + '/users/' + album.user.name + '/' + album_id + '/' + album_id + '.jpg'
        albumImage = 'data:image/jpg;base64,' + base64.b64encode( open(albumImageFile, 'rb').read() ).decode('utf-8')
        albumText = open(alfPath + '/users/' + album.user.name + '/' + album_id + '/' + album_id + '.html' , 'r').read()
        albumText = markdown(albumText)
        return flask.render_template(
                "download.html",
                bandName=album.band_name,
                albumName=album.album_name,
                infoText=albumText,
                albumImage=albumImage) 
    # check for code and start download
    # promocode:
    promocode = alfmin.Code.get(code=code, album=album, promocode=True)
    if promocode:
        code = promocode
    else:
        hashed = sha1(code.encode('utf-8')).hexdigest()
        # get code
        code = alfmin.Code.get(code=hashed, album=album)
    # check if valid
    if code is not None:
        if code.count < album.limit or promocode is not None:
            # we need to increment Code ...
            code.count += 1
            download_log = alfmin.Download(code=code, datetime=datetime.now())
            zipFile = alfPath + '/users/' + album.user.name + '/' + album_id + '/' + album_id + '.zip'
            return flask.send_file(
                    zipFile,
                    mimetype="application/zip",
                    as_attachment=True,
                    attachment_filename=str(album.band_name) + ' - ' + str(album.album_name) + '.zip')
    return '<script>alert("Invalid Code");window.history.back()</script>'  #TODO raplace with flash() + render


if __name__ == '__main__':
    # app.run(host='localhost', port=64004)
    app.run(host='localhost', port=64004, debug=True)



