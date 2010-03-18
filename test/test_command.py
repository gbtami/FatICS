from test import *

class TestCommand(Test):
    def test_command(self):
        t = self.connect_as_guest()
        t.write('badcommand\n')
        self.expect('Command not found', t)

        # abbreviate command
        t.write('fin\n')
        self.expect('Finger of ', t)

        # don't update idle time
        t.write('$$finger\n')
        self.expect('Finger of ', t)

        # commands are case-insensitive
        t.write('DATE\n')
        self.expect('Server time', t)

        # ignore extranous whitespace
        t.write(' \t  date  \t \n')
        self.expect('Server time', t)

        t.write('   \t \n')
        self.expect_not('Bad command', t)
        
        t.write('tell\n')
        self.expect('USAGE', t)

        t.close()
    

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
