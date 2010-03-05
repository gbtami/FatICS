from test import *

class TestGame(Test):
    def test_game(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()
        
        t.write('match admin white\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        t2.write('e7e5\n')
        self.expect('not your move', t2)

        self.close(t)
        self.close(t2)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent
