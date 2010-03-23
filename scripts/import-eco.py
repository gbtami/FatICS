#!/usr/bin/env python

"""This is a script to read a database of ECO openings in EPD format
and insert into the database in the format the server expects.  The
EPD file I use comes from scid by way of its eco2epd tool. """

import MySQLdb
import re
import variant.normal

epd_file = 'data/scid.epd'

def main():
    db = MySQLdb.connect(host='localhost', db='chess',
        read_default_file="~/.my.cnf")
    cursor = db.cursor()

    f = open(epd_file, 'r')

    cursor.execute("""DELETE FROM eco""")
    count = 0
    txt = None
    for line in f:
        line = line.decode('iso-8859-1').encode('utf-8')
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'(.+) +eco +([A-Z]\d\d\S*) +(.+);', line)
        if not m:
            print 'failed to match: %s' % line
        assert(m)
        (fen, eco, long) = (m.group(1), m.group(2), m.group(3))
        pos = variant.normal.Position(fen + ' 0 1')
        cursor.execute("""INSERT INTO eco SET eco=%s, long_=%s, hash=%s""",
            (eco,long,pos.hash))
        count += 1
    cursor.close()
    print 'imported %d codes' % count
    
if __name__ == "__main__":
    main()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent