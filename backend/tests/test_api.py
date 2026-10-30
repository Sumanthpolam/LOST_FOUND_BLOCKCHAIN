import os, tempfile, unittest
os.environ['DATABASE_PATH']=os.path.join(tempfile.gettempdir(),'findchain-test-'+str(os.getpid())+'.db')
import app

class ApiTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.client=app.app.test_client()
 def login(self,email,password):
  r=self.client.post('/api/auth/login',json={'email':email,'password':password}); return r.json['token']
 def test_demo_auth_and_lost_report(self):
  token=self.login('demo@findchain.local','FindChain123!'); h={'Authorization':'Bearer '+token}
  r=self.client.post('/api/items/lost',headers=h,json={'name':'Blue wallet test','category':'Wallets','location':'Library'}); self.assertEqual(r.status_code,201); self.assertEqual(r.json['blockchainStatus'],'local_demo')
  item=self.client.get('/api/items/'+r.json['itemId']); self.assertEqual(item.status_code,200); self.assertNotIn('private_details',item.json)
 def test_admin_guard_and_registration(self):
  self.assertEqual(self.client.get('/api/admin/overview').status_code,401)
  r=self.client.post('/api/auth/register',json={'name':'Test Person','email':'test-'+str(os.getpid())+'@example.com','password':'LongPassword123'}); self.assertEqual(r.status_code,201)

if __name__=='__main__': unittest.main()
