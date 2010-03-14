from test import *

class TestMatch(Test):
    def test_match(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()

        t.write('match guest\n')
        self.expect("can't match yourself", t)

        t.write('match nonexistentname\n')
        self.expect('No user named "nonexistentname"', t)

        t.write('set open 0\n')
        t2.write('set open 0\n')
        t.write('match admin\n')
        self.expect('admin is not open to match requests', t)

        t2.write('set open 1\n')
        self.expect('now open', t2)
        t.write('match admin\n')
        self.expect('now open to receive match requests', t)
        self.expect('Issuing: ', t)
        self.expect('Challenge: ', t2)

        self.close(t)
        self.close(t2)
    
    def test_withdraw_logout(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()
        t2.write('match guest\n')
        t2.write('quit\n')
        self.expect('Withdrawing your match offer to Guest', t2)
        self.expect('Thank you for using', t2)
        t2.close()

        self.expect('admin, who was challenging you, has departed', t)
        self.close(t)
    
    def test_decline_logout(self):
        t = self.connect_as_user('GuestABCD', '')
        t2 = self.connect_as_admin()

        t.write('match admin\n')
        self.expect('Challenge:', t2)
        t2.write('quit\n')
        self.expect('Declining the match offer from Guest', t2)
        t2.close()

        self.expect('admin, whom you were challenging, has departed', t)
        self.close(t)

    def test_accept(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()
        
        t.write('match admin\n')
        self.expect('Challenge:', t2)
        t2.write('accept\n')
        self.expect('Accepting the match offer', t2)
        self.expect('accepts your match offer', t)
        
        self.expect('Creating: ', t)
        self.expect('Creating: ', t2)

        self.close(t)
        self.close(t2)

    def test_withdraw(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()
        
        t.write('match admin\n')
        self.expect('Challenge:', t2)
        t.write('withdraw\n')
        self.expect('Withdrawing your match offer', t)
        self.expect('withdraws the match offer', t2)

        self.close(t)
        self.close(t2)
    
    def test_decline(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()
        
        t.write('match admin\n')
        self.expect('Challenge:', t2)
        t2.write('decline\n')
        self.expect('Declining the match offer', t2)
        self.expect('declines your match offer', t)

        self.close(t)
        self.close(t2)
    
    def test_counteroffer(self):
        t = self.connect_as_user('GuestABCD', '')
        t2 = self.connect_as_admin()
        
        t.write('match admin 1 0\n')
        self.expect('Challenge:', t2)
        t2.write('match Guest 2 0\n')
        self.expect('Declining the offer from GuestABCD and proposing a counteroffer', t2)
        self.expect('admin declines your offer and proposes a counteroffer', t)

        self.close(t)
        self.close(t2)
    
    def test_update_offer(self):
        t = self.connect_as_user('GuestABCD', '')
        t2 = self.connect_as_admin()
        
        t.write('match admin 1 0\n')
        self.expect('Challenge:', t2)
        t.write('match admin 1 0 white\n')
        self.expect('Updating the offer already made to admin', t)
        self.expect('GuestABCD updates the offer', t2)

        self.close(t)
        self.close(t2)
    
    def test_offer_identical(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()
        
        t.write('match admin 1 0 black\n')
        t.write('match admin 1 0 black\n')
        self.expect('already offering an identical match to admin', t)

        self.close(t)
        self.close(t2)
    
    def test_accept_identical(self):
        t = self.connect_as_guest()
        t2 = self.connect_as_admin()
        
        t.write('match admin 1 2 white\n')
        self.expect('Challenge:', t2)
        t2.write('match Guest 1 2 black\n')
        self.expect('Accepting the match offer', t2)
        self.expect('accepts your match offer', t)

        self.close(t)
        self.close(t2)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 smarttab autoindent