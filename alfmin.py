#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import redis
import hashlib
import os
import random
import datetime
import glob
import re

# replace with send img!!!!
import base64 

from alf_db import Album, Code, db_session, Download, User, select


alfPath = os.path.dirname(os.path.realpath(__file__))

@db_session
def listAlfUsers():
    """
    returns a list of available users
    """
    alfUsers = [user.name for user in select(u for u in User)]
    # repair if directory is missing
    for user in alfUsers:
        if not os.path.isdir(alfPath + '/users/' + user):
            os.mkdir(alfPath + '/users/' + user)
    return alfUsers

@db_session
def addAlfUser(userName, password):
    """
    add a new user to ALF
    (str userName, str password) -> True or False

    allowed Characters: 'abcdefghijklmnopqrstuvwxyz0123456789'

    """
    allowedChars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    for c in userName:
        if c not in allowedChars:
            userName.replace(c, '')
    user = User.get(name=userName)
    if user:
        return False
    passwordHash = hashlib.sha1(password.encode('utf-8')).hexdigest()
    user = User(name=userName, password_hash=passwordHash)
    if not os.path.isdir(alfPath + '/users/' + userName[5:]):
        os.mkdir(alfPath + '/users/' + userName[5:])
    return True

@db_session
def deleteAlfUser(userName):
    """
    delete an ALF user
    (userName) -> True or False
    """
    user = User.get(name=userName)
    if user:
        # ponyORM does cascade deleting by default ... TODO: Test
        # Album.select(lambda a: a.user == user).delete(bulk=True)
        user.delete()
        for root, dirs, files in os.walk(alfPath +'/users/' + userName, topdown=False):
            for name in files:
                os.remove(os.path.join(root,name))
            for name in dirs:
                os.rmdir(os.path.join(root,name))
        os.rmdir( alfPath + '/users/' + userName  )
        return True
    return False

@db_session
def listAlfUserAlbums(userName):
    """
    returns all albums (including stats, image and info) for an alf user
    (userName) -> dict
    """
    _releases = select(a for a in Album if a.user.name == userName)
    releases = dict()
    # release is an album_id
    for album in _releases:
        release = album.album_id
        albumImageFile = alfPath + '/users/' + userName + '/' + release + '/' + release + '.jpg'
        albumImage = 'data:image/jpg;base64,' + base64.b64encode( open(albumImageFile, 'rb').read() ).decode('utf-8')
        uniqueStats, totalStats, numberOfCodes, promoStats = getAlbumStats(album)
        releases[album.album_id] = {
                            'uniqueStats': uniqueStats,
                            'totalStats': totalStats,
                            'numberOfCodes': numberOfCodes,
                            'promo': promoStats,
                            'albumImage': albumImage,
                            'bandName': album.band_name,
                            'albumName': album.album_name,
                            'limit': album.limit,
                            'codeFiles': [f for f in os.listdir(alfPath + '/users/' + userName + '/' + release + '/') if re.match(r''+release+'--' ,f)] 
                            }
    return releases
            

#TODO
def deleteAlfAlbum(albumName):
    """
    delete an ALF album
    (albumName) -> True or False
    """
    alfAlbums = []
    for key in r.keys():
        if key[:6] == 'ALBUM:':
            alfAlbums.append(key[6:])
    if not albumName in alfAlbums:
        return False
    else:
        userName = r.hget('ALBUM:' + albumName, 'user')
        r.delete('ALBUM:' + albumName)
        for root, dirs, files in os.walk(alfPath + '/users/' + userName + '/' + albumName, topdown=False):
            for name in files:
                os.remove(os.path.join(root,name))
            for name in dirs:
                os.rmdir(os.path.join(root,name))
        return True


@db_session
def addAlfAlbum(albumID, bandName, albumName, user, limit, albumText, flaskFileImage, flaskFileZip):
    """
    add an Album to Alf.
    ( <str> albumID, bandName, albumName, user, limit, albumText, <binary> albumImage, flaskFileObject) -> (True or False, message)
    albumID allowed Characters = 'abcdefghijklmnopqrstuvwxyz0123456789'
    """
    allowedChars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    for c in albumID:
        if c not in allowedChars:
            albumID.replace(c, '')
    album = Album.get(album_id=albumID)
    if album:
        return (False, 'ID exists, please choose another one')
    user = User.get(name=user)
    if user is None:
        return (False, 'user does not exist')
    if not limit.isdigit():
        return (False, 'download limit needs to be an integer')
    album = Album (
        album_id = albumID,
        band_name = bandName,
        album_name = albumName,
        limit = limit,
        user = user
            )
    albumPath = alfPath + '/users/' + user.name + '/' + albumID
    os.mkdir(albumPath)
    with open (albumPath + '/' + albumID + '.html', "xt") as htmlFile:
        htmlFile.write(albumText)
    flaskFileZip.save(os.path.join(albumPath, albumID + '.zip'))
    flaskFileImage.save(os.path.join(albumPath, albumID + '.jpg'))
    return (True, 'album added!')

@db_session
def getAlbumStats(album):
    '''
    Returns some stats:
    (used Codes , total Downloads incl. multiple , number of codes, promo-downloads)
    '''
    uniqueStats = len(select(c for c in Code if c.album == album and c.count > 0 and c.promocode == False))
    totalStats =  sum( [code.count for code in select(c for c in Code if c.album == album and c.promocode == False)] )
    numberOfCodes = len( select(c for c in Code if c.album == album and c.promocode == False) )
    promoStats = [
            {'code': code.code, 'count': code.count}
            for code in select(c for c in Code if c.album == album and c.promocode == True)
            ]
    return uniqueStats, totalStats, numberOfCodes, promoStats


def __createNewCode(n=8):
    """
    Returns a Random string of lenght n
    (int n) -> str
    """
    newCode = ""
    for i in range(n):
        newCode += random.SystemRandom().choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return newCode

@db_session
def createCodes(albumID, user, amount = 3):
    """
    returns a list of new uniqe generated codes for a given album
    (str albumName , int amount=3) -> (True,list()) or (False, empty-list())
    """
    album = Album.get(album_id=albumID)
    if album is None:
        return (False, [])
    newCodes = []
    while len(newCodes) < amount:
            newCode = __createNewCode()
            newHash = hashlib.sha1(newCode.encode('utf-8')).hexdigest()
            if not Code.exists(code=newHash, album=album):
                code = Code(code=newHash, album=album, count=0, promocode=False)
                newCodes.append(newCode)
    albumPath = alfPath + '/users/' + user + '/' + albumID
    codeFile = albumID + '--' + datetime.datetime.today().strftime('%Y-%m-%d--%H.%M.%S')  + '--' + str(amount) + '-codes.txt'
    with open( os.path.join(albumPath, codeFile) , 'w') as f:
        f.write('\n'.join(newCodes))
    return (True, newCodes)



