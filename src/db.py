from MySQLdb import *

import var

class DB(object):
	def __init__(self):
		self.db = connect(host="localhost", db="chess", user="chess", passwd="Luu9yae7")

        def user_get(self, name):
                cursor = self.db.cursor(cursors.DictCursor)
                cursor.execute("""SELECT user_id,user_name,user_passwd,user_last_logout,user_admin_level FROM user WHERE user_name=%s""", (name,))
                row = cursor.fetchone()
                cursor.close()
                return row
        
        def user_load_vars(self, user_id):
                cursor = self.db.cursor(cursors.DictCursor)
                cursor.execute("""SELECT tell,shout FROM user WHERE user_id=%s""", (user_id,))
                row = cursor.fetchone()
                cursor.close()
                return row
        
        def user_set_var(self, user_id, name, val):
                assert(var.vars[name].name == name)
                cursor = self.db.cursor()
                up = """UPDATE user SET %s""" % (var.vars[name].dbname)
                cursor.execute(up + """=%s WHERE user_id=%s""", (val,user_id))
                cursor.close()

        def user_get_matching(self, prefix):
                cursor = self.db.cursor(cursors.DictCursor)
                cursor.execute("""SELECT user_id,user_name,user_passwd,user_last_logout,user_admin_level FROM user WHERE user_name LIKE %s LIMIT 8""", (prefix + '%',))
                rows = cursor.fetchall()
                cursor.close()
                return rows
        
        def user_add(self, name, email, passwd, real_name, admin_level):
                cursor = self.db.cursor()
                cursor.execute("""INSERT INTO user SET user_name=%s,user_email=%s,user_passwd=%s,user_real_name=%s,user_admin_level=%s""", (name,email,passwd,real_name,admin_level))
                cursor.close()

        def user_set_passwd(self, id, passwd):
                cursor = self.db.cursor()
                cursor.execute("""UPDATE user SET user_passwd=%s WHERE user_id=%s""", (passwd, id))
                cursor.close()

        def user_set_admin_level(self, id, level):
                cursor = self.db.cursor()
                cursor.execute("""UPDATE user SET user_admin_level=%s WHERE user_id=%s""", (str(level), id))
                cursor.close()

        def user_set_last_logout(self, id):
                cursor = self.db.cursor()
                cursor.execute("""UPDATE user SET user_last_logout=NOW() WHERE user_id='%s'""", (id,))
                cursor.close()
        
        def user_delete(self, id):
                cursor = self.db.cursor()
                cursor.execute("""DELETE FROM user WHERE user_id=%s""", (id,))
                cursor.close()
        
        def user_get_channels(self, id):
                cursor = self.db.cursor() #cursors.DictCursor)
                cursor.execute("""SELECT channel_id FROM channel_user WHERE user_id=%s""", (id,))
                rows = cursor.fetchall()
                cursor.close()
                return [r[0] for r in rows]
        
        def channel_new(self, id, name):
                cursor = self.db.cursor()
                cursor.execute("""INSERT INTO channel SET channel_id=%s,name=%s,descr=NULL""", (id, name,))
                cursor.close()

        def channel_add_user(self, ch_id, user_id):
                cursor = self.db.cursor()
                cursor.execute("""INSERT INTO channel_user SET user_id=%s,channel_id=%s""", (user_id,ch_id))
                cursor.close()
        
        def channel_del_user(self, ch_id, user_id):
                cursor = self.db.cursor()
                cursor.execute("""DELETE FROM channel_user WHERE user_id=%s AND channel_id=%s""", (user_id,ch_id))
                cursor.close()
        
        def channel_list(self):
                cursor = self.db.cursor(cursors.DictCursor)
                cursor.execute("""SELECT channel_id,name,descr FROM channel""")
                rows = cursor.fetchall()
                cursor.close()
                return rows
        
        def channel_get_members(self, id):
                cursor = self.db.cursor()
                cursor.execute("""SELECT user_name FROM channel_user LEFT JOIN user USING (user_id) WHERE channel_id=%s""", (id,))
                rows = cursor.fetchall()
                cursor.close()
                return [r[0] for r in rows]

db = DB()

# vim: expandtab tabstop=8 softtabstop=8 shiftwidth=8 smarttab autoindent ft=python