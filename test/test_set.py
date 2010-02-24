from test import *

class TestSet(Test):
	def test_set(self):
		t = self.connect_as_guest()
                t.write("set tell 0\n")
                self.expect("You will not hear direct tells from unregistered", t)
                t.write("set tell 1\n")
                self.expect("You will now hear direct tells from unregistered", t)
               
                # abbreviated var
                t.write("set te 0\n")
                self.expect("You will not hear direct tells from unregistered", t)
                
                t.write("set shout 0\n")
                self.expect("You will not hear shouts", t)
                t.write("set shout 1\n")
                self.expect("You will now hear shouts", t)

                self.close(t)

        def test_bad_set(self):
		t = self.connect_as_guest()
                t.write('set too bar\n')
                self.expect("No such variable", t)
                t.write('set shout bar\n')
                self.expect("Bad value given", t)
                self.close(t)
        
        def test_set_persistence(self):
		t = self.connect_as_admin()
                t.write('set shout 0\n')
                t.write('vars\n')
                self.expect('shout=0', t)
                self.close(t)
		
                t = self.connect_as_admin()
                t.write('vars\n')
                self.expect('shout=0', t)
                t.write('set shout 1\n')
                self.close(t)
                
                t = self.connect_as_admin()
                t.write('vars\n')
                self.expect('shout=1', t)
                self.close(t)

# vim: expandtab tabstop=8 softtabstop=8 shiftwidth=8 smarttab autoindent ft=python