
from datetime import datetime
from os.path import dirname, exists, join, realpath

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
alfPath = dirname(realpath(__file__))
db.bind(provider='sqlite', filename=join(alfPath,'db','alf.sqlite3'), create_db=True)

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
