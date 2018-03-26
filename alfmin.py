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

# This is a python module, r and alfPath should be provided by ALF

# r = redis.Redis(charset="utf-8", decode_responses=True, db=5)
r = None
# alfPath = os.path.dirname(os.path.realpath(__file__))
alfPath = None


def listAlfUsers():
    """
    returns a list of available users
    """
    alfUsers = []
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


def listAlfUserAlbums(userName):
    """
    returns all albums (including stats, image and info) for an alf user
    (userName) -> dict
    """
    releases = r.hgetall('USER:' + userName)
    releases.pop('password')
    for release in releases:
        albumImageFile = alfPath + '/users/' + userName + '/' + release + '/' + release + '.jpg'
        albumImage = 'data:image/jpg;base64,' + base64.b64encode( open(albumImageFile, 'rb').read() ).decode('utf-8')
        uniqueStats, totalStats, numberOfCodes, promoStats = getAlbumStats('ALBUM:' + release,userName)
        releases[release] = {
                            'uniqueStats': uniqueStats,
                            'totalStats': totalStats,
                            'numberOfCodes': numberOfCodes,
                            'promo': promoStats,
                            'albumImage': albumImage,
                            'bandName': r.hget('ALBUM:' + release, 'bandname'),
                            'albumName': r.hget('ALBUM:' + release, 'albumname'),
                            'limit': r.hget('ALBUM:' + release, 'limit'),
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
                if code not in ['stats', 'limit', 'user' ,'bandname', 'albumname','damniam','promocodes']:
                    dlCount = int(album[code])
                    if dlCount >= 0:
                        numberOfCodes += 1
                    if dlCount > 0:
                        totalStats += dlCount
                        uniqueStats += 1
            # handle promocodes (negative counters)
            promoStats = []
            if 'promocodes' in album:
                promocodes = album['promocodes'].split(',')
                for promocode in promocodes:
                    promokey = hashlib.sha1(promocode.encode('utf-8')).hexdigest()
                    promokey_downloads = 1000000 + int(album[promokey])
                    promoStats.append({'code': promocode,'count':promokey_downloads})
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



