#!/usr/bin/env python

# Set up head admin user.

try:
    import readline
except:
    pass

import sys
import re
import MySQLdb
import getpass
import bcrypt

sys.path.insert(0, 'src/')
import config
import admin

db = MySQLdb.connect(host=config.db_host, db=config.db_db,
    read_default_file="~/.my.cnf")
assert(db)
cursor = db.cursor()
cursor.execute("""SET time_zone='+00:00'""")
db.set_character_set('utf8')

cursor.execute("""SELECT COUNT(*) As c FROM user""")
count = int(cursor.fetchone()[0])
if count != 0:
    print('Not continuing; there is already at least one user')
    sys.exit(1)

while True:
    username = raw_input('Head admin username: ')
    if len(username) > 17 or len(username) < 3 or not re.match('^[A-Za-z]+$', username):
        print("Error: invalid username\n")
        continue
    break

while True:
    email = raw_input('Email address: ')
    if '@' not in email or '.' not in email:
        print("Error: invalid email\n")
        continue
    break

while True:
    realname = raw_input('Real name: ')
    if len(realname) < 3:
        print("Error: invalid name\n")
        continue
    break

while True:
    passwd = getpass.getpass('Password: ')
    if len(passwd) < 4:
        print("Error: invalid password\n")
        continue
    passwd = bcrypt.hashpw(passwd, bcrypt.gensalt())
    break

uid = cursor.execute("""INSERT INTO user
    SET user_name=%s,user_email=%s,user_passwd=%s,
    user_real_name=%s,user_admin_level=%s""",
    (username, email, passwd, realname, admin.Level.head))

cursor.close()

print('successfully created head admin %s(*)' % username)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent ft=python
