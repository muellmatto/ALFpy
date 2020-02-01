#!/usr/bin/env python
from datetime import datetime

from redis import Redis

from pony.orm import (
        Database,
        db_session,
        Required,
        Optional,
        PrimaryKey,
        composite_key,
        Set,
        select
        )


db = Database()
# db.bind(provider='sqlite', filename=':memory:')
db.bind(provider='sqlite', filename='test.sqlite3', create_db=True)

r = Redis(charset="utf-8", decode_responses=True ,db=5)
# r = Redis(charset="utf-8", decode_responses=True ,db=redisDbNumber, unix_socket_path=socketPath)


class User(db.Entity):
    name = PrimaryKey(str)
    password_hash = Required(str)
    albums = Set('Album')


class Album(db.Entity):
    album_id = PrimaryKey(str)
    band_name = Required(str)
    album_name = Required(str)
    limit = Required(int)
    # album_text = Required(str) # -> text-file
    user = Required('User')
    codes = Set('Code')


class Code(db.Entity):
    code = Required(str)
    album = Required('Album')
    PrimaryKey(code, album)
    #  composite_key(a, b) will be represented as the UNIQUE ("a", "b") constraint.
    count = Required(int)
    promocode = Required(bool)
    downloads = Set('Downloads')


class Downloads(db.Entity):
    code = Required('Code')
    datetime = Required(datetime)

    
db.generate_mapping(create_tables=True)

#===================================================#

def migrate_user_by_key(key):
    username = key.lstrip('USER:')
    print(f'username: {username}')
    password = r.hget(key, 'password')
    print(username, password)
    with db_session:
        user = User.get(name=username)
        if user is None:
            user = User(name=username, password_hash=password)
            print(f'created {user}')
        else:
            user.password_hash = password
            print(f'updated {user}')

@db_session
def migrate_album_by_key(key):
    print(f'key: {key}')
    album_id = key.lstrip('ALBUM:')
    album_redis = r.hgetall(key)
    # get album data
    band_name = album_redis.pop('bandname')
    album_name = album_redis.pop('albumname')
    limit = album_redis.pop('limit')
    _user = album_redis.pop('user')
    user = User.get(name=_user)
    if user is None:
        print(f'user {_user} does not exist!! BREAK')
        return
    # create / update album
    album = Album.get(album_id=album_id)
    if album is None:
        album = Album(
                album_id = album_id,
                band_name = band_name,
                album_name = album_name,
                limit = limit,
                user = user
                )
        print(f'created {album}')
    else:
        print(f'{album} already in db')
        return
    # create Promocodes first.
    if 'promocodes' in album_redis:
        promocodes = album_redis.pop('promocodes')
        for promocode in promocodes.split(','):
            code = Code(code = promocode, album = album, count = 0, promocode = True )
    # only codes left ...
    for code, count in album_redis.items():
        if count.isdigit():
            code = Code(code = code, album = album, count = int(count), promocode = False)


'''

Redis stuff:

     'promocodes': 'DMNMDMNM,PROMOIAM'}
     {'bandname': 'DAMNIAM',
              'albumname': 'PLANET PISS',
               'limit': '4',
                'user': 'damniam',
                 '5acf303854565d526229ccbcd2bde2a140fadb17': '0',
                  '98e7339acb89ee6a09ed03070e2a529d31f2e5b3': '0',

'''

# migrationorder: users, albums
users = []
albums = []
for key in r.keys():
    # check if Redis-key really is an hash
    if not r.type(key) == 'hash':
        print("{} is not a hashmap".format(key))
    if key.startswith('USER:'):
        users.append(key)
    elif key.startswith('ALBUM:'):
        albums.append(key)
    else:
        print(f'{key} seems not to be an ALF - Key')

print(users)
print(albums)
print('/////////////')
for key in users:
    print('\n=============\n')
    print(f'key: {key}')
    print('---')
    migrate_user_by_key(key)

with db_session:
    for user in select(u for u in User)[:]:
        print(user)

print('\n\n/////////////\n\n')


for key in albums:
    migrate_album_by_key(key)
