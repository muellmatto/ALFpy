#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import redis
import hashlib
import os
import sys
import random

r = redis.Redis(charset="utf-8", decode_responses=True, db=5)

alfPath = os.path.dirname(os.path.realpath(__file__))


def listAlfUsers():
    '''
    list available user
    '''
    alfUsers = []
    for key in r.keys():
        if key[:5] == 'USER:':
            alfUsers.append(key[5:])

    # repair if directory is missing
    for user in alfUsers:
        if not os.path.isdir(alfPath + '/users/' + user):
            print('user ' + user + 'has no directory!' )
            os.mkdir(alfPath + '/users/' + user)
            print('directory created!')

    print('users:')
    print(alfUsers)


def addAlfUser():
    '''
    add a new user to ALF
    '''
    userName = input('Enter new Username: ')
    if not userName.islower() or not userName.isalpha():
        print('Allowed characters: [a..z]')
    else:
        userName = 'USER:' + userName
        if userName in r.keys():
            print('User %s already exists' % userName[5:])
        else:
            password1 = input('Enter password: ')
            password2 = input('Repeat password: ')
            if not password1 == password2:
                print('passwords did not match')
            else:
                passwordHash = hashlib.sha1(password1.encode('utf-8')).hexdigest()
                r.hset(userName, 'password', passwordHash)
                print('user: ' + userName[5:] + ' was created')
                if not os.path.isdir(alfPath + '/users/' + userName[5:]):
                    print('user ' + userName[5:] + 'has no directory!' )
                    os.mkdir(alfPath + '/users/' + userName[5:])
                    print('directory created!')


def deleteAlfUser():
    listAlfUsers()
    userName = input('Which user do you want to delete? ')
    userKey = 'USER:' + userName
    if userKey not in r.keys():
        print('user does not exist.')
    else:
        alfAlbums = []
        for key in r.keys():
            if key[:6] == 'ALBUM:':
                if r.hget(key, 'user') == userName:
                    alfAlbums.append(key[6:])
        print('these albums will be deleted:')
        print(alfAlbums)
        yes = input('are you sure? (type "yes") :')
        if yes == 'yes':
            print('deleting user ' + userName )
            r.delete(userKey)
            # print(userKey)
            for root, dirs, files in os.walk(alfPath +'/users/' + userName, topdown=False):
                for name in files:
                    print('deleting: ' + os.path.join(root,name))
                    os.remove(os.path.join(root,name))
                for name in dirs:
                    print('deleting: ' + os.path.join(root,name))
                    os.rmdir(os.path.join(root,name))


def deleteAlfAlbum():
    alfAlbums = []
    for key in r.keys():
        if key[:6] == 'ALBUM:':
            alfAlbums.append(key[6:])
    print('albums:')
    print(alfAlbums)
    print('Which album do you want to delete?')
    albumName = input('? ')
    if not albumName in alfAlbums:
        print('Album does not exist.')
    else:
        userName = r.hget('ALBUM:' + albumName, 'user')
        #print(albumName)
        #print(userName)
        yes = input('are you sure? (type "yes") :')
        if yes == 'yes':
            r.delete('ALBUM:' + albumName)
            for root, dirs, files in os.walk(alfPath + '/users/' + userName + '/' + albumName, topdown=False):
                for name in files:
                    print('deleting: ' + os.path.join(root,name))
                    os.remove(os.path.join(root,name))
                for name in dirs:
                    print('deleting: ' + os.path.join(root,name))
                    os.rmdir(os.path.join(root,name))

def listAlfAlbums():
    '''
    list available albums
    '''
    alfAlbums = []
    for key in r.keys():
        if key[:6] == 'ALBUM:':
            alfAlbums.append(key[6:])
    print('albums:')
    print(alfAlbums)


def addAlfAlbum():
    album=input('enter album id [a..z]: ')
    if album.isalpha() and album.islower() and 'ALBUM:'+album not in r.keys():
        bandName = input('enter bandname: ') # bandname
        albumName = input('enter albumname: ') # albumname
        user = input('enter ALF-user, owning this album: ') # user
        if not 'USER:' + user in r.keys():
            print('user does not exist!')
        else:
            limit = input('enter maximum allowed downloads per code: ')
            if not limit.isdigit():
                print('not an integer')
            else:
                r.hset('ALBUM:' + album, 'bandname', bandName)
                r.hset('ALBUM:' + album, 'albumname', albumName)
                r.hset('ALBUM:' + album, 'limit', limit)
                r.hset('ALBUM:' + album, 'user', user)
                r.hset('USER:' + user, album, 'ALBUM:'+album)
                print('album ONLY added to redis!')
    else:
        print('albumname not available or invalid characters')
        


def createNewCode(n=8):
    newCode = ""
    for i in range(n):
        newCode += random.SystemRandom().choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    return newCode


def createCodes(albumRedisKey, amount = 3):
    newCodes = []
    for n in range(amount):
        while True:
            newCode = createNewCode()
            newHash = hashlib.sha1(newCode.encode('utf-8')).hexdigest()
            if r.hget(albumRedisKey, newHash) is None:
                r.hset(albumRedisKey, newHash, "0")
                newCodes.append(newCode)
                break
    return newCodes


def addCodes():
    print('which album shout get new codes?')
    alfAlbums = []
    for key in r.keys():
        if key[:6] == 'ALBUM:':
            alfAlbums.append(key[6:])
    print(alfAlbums)
    album = input('? ')
    if not album in alfAlbums:
        print('choose an existing album!')
    else:
        numberOfCodes = input('how many codes do you want to generate? ')
        if not numberOfCodes.isdigit():
            print('enter a number!')
        else:
            newCodes = createCodes(albumRedisKey = 'ALBUM:' + album, amount = int(numberOfCodes))
            filename = './' + album + '-newcodes.txt'
            f = open(filename,'w')
            for code in newCodes:
                f.write(code + '\n')
            f.close()
            print('Codes written to: ' + filename)
            # print(newCodes)





alfUsage = sys.argv[0] + ''' <command>

commands:

listusers -     lists all available users
listalbums -    list all available albums

adduser -       adds a new ALF user
addalbum -      adds a new album to alf

deleteuser -    deletes an ALF user
deletealbum -   deletes an album

addcodes -      creates new codes for an album
'''


if len(sys.argv) == 2:
    if sys.argv[1] == 'listusers':
        listAlfUsers()
    elif sys.argv[1] == 'listalbums':
        listAlfAlbums()
    elif sys.argv[1] == 'adduser':
        addAlfUser()
    elif sys.argv[1] == 'deleteuser':
        deleteAlfUser()
    elif sys.argv[1] == 'addalbum':
        addAlfAlbum()
    elif sys.argv[1] == 'deletealbum':
        deleteAlfAlbum()
    elif sys.argv[1] == 'addcodes':
        addCodes()
    else:
        print(alfUsage)
else:
    print(alfUsage)


