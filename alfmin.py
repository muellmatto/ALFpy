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

from alf_db import Album, Code, db_session, Downloads, User, select

# TODO
# create and delete functions ... 

alfPath = os.path.dirname(os.path.realpath(__file__))

@db_session
def listAlfUsers():
    """
    returns a list of available users
    """
    alfUsers = [user.name for user in select(u for u in User)]
    for key in r.keys():
        if key[:5] == 'USER:':
            alfUsers.append(key[5:])

    # repair if directory is missing
    for user in alfUsers:
        if not os.path.isdir(alfPath + '/users/' + user):
            os.mkdir(alfPath + '/users/' + user)
    return alfUsers


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
    userName = 'USER:' + userName
    if userName in r.keys():
        return False
    else:
        passwordHash = hashlib.sha1(password.encode('utf-8')).hexdigest()
        r.hset(userName, 'password', passwordHash)
        if not os.path.isdir(alfPath + '/users/' + userName[5:]):
            os.mkdir(alfPath + '/users/' + userName[5:])
        return True


def deleteAlfUser(userName):
    """
    delete an ALF user
    (userName) -> True or False
    """
    userKey = 'USER:' + userName
    if userKey not in r.keys():
        return False
    else:
        alfAlbums = []
        for key in r.keys():
            if key[:6] == 'ALBUM:':
                if r.hget(key, 'user') == userName:
                    alfAlbums.append(key[6:])
        r.delete(userKey)
        for root, dirs, files in os.walk(alfPath +'/users/' + userName, topdown=False):
            for name in files:
                os.remove(os.path.join(root,name))
            for name in dirs:
                os.rmdir(os.path.join(root,name))
        os.rmdir( alfPath + '/users/' + userName  )
        return True

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


def listAlfAlbums():
    """
    returns a list of available albums
    () -> list
    """
    alfAlbums = []
    for key in r.keys():
        if key[:6] == 'ALBUM:':
            alfAlbums.append(key[6:])
    return alfAlbums


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
    if 'ALBUM:'+albumID  in r.keys():
        return (False, 'ID exists, please choose another one')
    if not 'USER:' + user in r.keys():
        return (False, 'user does not exist')
    if not limit.isdigit():
        return (False, 'download limit needs to be an integer')
    r.hset('ALBUM:' + albumID, 'bandname', bandName)
    r.hset('ALBUM:' + albumID, 'albumname', albumName)
    r.hset('ALBUM:' + albumID, 'limit', limit)
    r.hset('ALBUM:' + albumID, 'user', user)
    r.hset('USER:' + user, albumID, 'ALBUM:'+albumID)

    albumPath = alfPath + '/users/' + user + '/' + albumID
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
    print(album, promoStats)
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


def createCodes(albumID, user, amount = 3):
    """
    returns a list of new uniqe generated codes for a given album
    (str albumName , int amount=3) -> (True,list()) or (False, empty-list())
    """
    albumRedisKey='ALBUM:' + albumID
    if albumRedisKey not in r.keys():
        return (False, [])
    newCodes = []
    for n in range(amount):
        while True:
            newCode = __createNewCode()
            newHash = hashlib.sha1(newCode.encode('utf-8')).hexdigest()
            if r.hget(albumRedisKey, newHash) is None:
                r.hset(albumRedisKey, newHash, "0")
                newCodes.append(newCode)
                break
    albumPath = alfPath + '/users/' + user + '/' + albumID
    codeFile = albumID + '--' + datetime.datetime.today().strftime('%Y-%m-%d--%H.%M.%S')  + '--' + str(amount) + '-codes.txt'
    with open( os.path.join(albumPath, codeFile) , 'w') as f:
        f.write('\n'.join(newCodes))
    return (True, newCodes)



