import os, sqlite3, hashlib, uuid, json
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt

ROOT=os.path.dirname(__file__); DB=os.getenv('DATABASE_PATH',os.path.join(ROOT,'findchain.db')); SECRET=os.getenv('SECRET_KEY','dev-only-change-me')
app=Flask(__name__); CORS(app,origins=os.getenv('CORS_ORIGINS','http://localhost:5173').split(','))
def now(): return datetime.now(timezone.utc).isoformat()
def db():
 if 'db' not in g:
  g.db=sqlite3.connect(DB); g.db.row_factory=sqlite3.Row; g.db.execute('PRAGMA foreign_keys=ON')
 return g.db
@app.teardown_appcontext
def close(e=None):
 c=g.pop('db',None)
 if c: c.close()
def initialize():
 c=sqlite3.connect(DB); c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,phone TEXT,password TEXT,role TEXT DEFAULT 'user',created_at TEXT);
 CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY,owner_id INTEGER REFERENCES users(id),kind TEXT,name TEXT,category TEXT,description TEXT,brand TEXT,color TEXT,location TEXT,date_event TEXT,status TEXT DEFAULT 'Available',private_details TEXT,record_hash TEXT,tx_hash TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS claims(id TEXT PRIMARY KEY,item_id TEXT REFERENCES items(id),user_id INTEGER REFERENCES users(id),features TEXT,purchase TEXT,status TEXT DEFAULT 'Pending',created_at TEXT,reviewer_id INTEGER,reviewed_at TEXT);
 CREATE TABLE IF NOT EXISTS handovers(id TEXT PRIMARY KEY,item_id TEXT,claim_id TEXT,finder_confirmed INTEGER DEFAULT 0,claimant_confirmed INTEGER DEFAULT 0,status TEXT DEFAULT 'Pending',created_at TEXT);
 CREATE TABLE IF NOT EXISTS blockchain_transactions(id INTEGER PRIMARY KEY,item_id TEXT,type TEXT,tx_hash TEXT,block_number INTEGER,status TEXT,created_at TEXT);
 CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY,user_id INTEGER,message TEXT,created_at TEXT,read INTEGER DEFAULT 0);
 CREATE INDEX IF NOT EXISTS item_search ON items(kind,category,location);''')
 for email,name,role,password in [('demo@findchain.local','Demo User','user','FindChain123!'),('admin@findchain.local','FindChain Admin','admin','Admin123!')]:
  if not c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone(): c.execute('INSERT INTO users(name,email,password,role,created_at) VALUES(?,?,?,?,?)',(name,email,generate_password_hash(password),role,now()))
 c.commit(); c.close()
def auth(admin=False):
 def decorate(fn):
  @wraps(fn)
  def wrapped(*a,**kw):
   try:
    data=jwt.decode(request.headers.get('Authorization','').split(' ')[1],SECRET,algorithms=['HS256']); user=db().execute('SELECT * FROM users WHERE id=?',(data['sub'],)).fetchone()
   except Exception: return jsonify(error='Authentication required'),401
   if not user or (admin and user['role']!='admin'): return jsonify(error='Administrator access required' if admin else 'Unauthorized'),403
   g.user=user; return fn(*a,**kw)
  return wrapped
 return decorate
def public(row):
 d=dict(row); d.pop('private_details',None); d.pop('password',None); return d
@app.get('/api/health')
def health(): return jsonify(status='ok',blockchain='local demo mode')
@app.post('/api/auth/register')
def register():
 d=request.get_json() or {}; email=str(d.get('email','')).strip().lower(); password=d.get('password','')
 if len(str(d.get('name','')).strip())<2 or '@' not in email or len(password)<10: return jsonify(error='Provide a name, valid email, and password of at least 10 characters'),400
 try:
  c=db(); cur=c.execute('INSERT INTO users(name,email,phone,password,created_at) VALUES(?,?,?,?,?)',(d['name'].strip(),email,d.get('phone',''),generate_password_hash(password),now())); c.commit(); return issue(c.execute('SELECT * FROM users WHERE id=?',(cur.lastrowid,)).fetchone()),201
 except sqlite3.IntegrityError: return jsonify(error='Email already registered'),409
def issue(u):
 t=jwt.encode({'sub':u['id'],'exp':int(datetime.now(timezone.utc).timestamp())+86400},SECRET,algorithm='HS256'); return jsonify(token=t,user={'id':u['id'],'name':u['name'],'email':u['email'],'role':u['role']})
@app.post('/api/auth/login')
def login():
 d=request.get_json() or {}; u=db().execute('SELECT * FROM users WHERE email=?',(str(d.get('email','')).lower(),)).fetchone()
 if not u or not check_password_hash(u['password'],d.get('password','')): return jsonify(error='Invalid email or password'),401
 return issue(u)
@app.get('/api/me')
@auth()
def me(): return jsonify(id=g.user['id'],name=g.user['name'],email=g.user['email'],phone=g.user['phone'],role=g.user['role'])
@app.put('/api/me')
@auth()
def update_me():
 d=request.get_json() or {}; db().execute('UPDATE users SET name=?,phone=? WHERE id=?',(str(d.get('name',g.user['name']))[:100],str(d.get('phone',g.user['phone']))[:40],g.user['id'])); db().commit(); return me()
@app.get('/api/stats')
def stats():
 c=db(); return jsonify(lost=c.execute("SELECT count(*) FROM items WHERE kind='lost'").fetchone()[0],found=c.execute("SELECT count(*) FROM items WHERE kind='found'").fetchone()[0],returned=c.execute("SELECT count(*) FROM items WHERE status='Returned'").fetchone()[0],verified=c.execute("SELECT count(*) FROM blockchain_transactions WHERE status='confirmed'").fetchone()[0])
@app.get('/api/items')
def items():
 q=request.args; sql='SELECT * FROM items WHERE 1=1'; args=[]
 for k in ('kind','category'):
  if q.get(k): sql+=f' AND {k}=?'; args.append(q[k])
 if q.get('location'): sql+=' AND location LIKE ?'; args.append('%'+q['location']+'%')
 if q.get('q'): sql+=' AND (name LIKE ? OR description LIKE ? OR brand LIKE ?)'; args+=['%'+q['q']+'%']*3
 if q.get('date'): sql+=' AND date_event=?'; args.append(q['date'])
 return jsonify([public(r) for r in db().execute(sql+' ORDER BY created_at DESC',args)])
@app.post('/api/items/<kind>')
@auth()
def create_item(kind):
 if kind not in ('lost','found'): return jsonify(error='Invalid report type'),404
 d=request.get_json() or {}; name=str(d.get('name','')).strip(); category=str(d.get('category','')).strip(); location=str(d.get('location','')).strip()
 if not name or not category or not location: return jsonify(error='Name, category, and location are required'),400
 iid='FC-'+uuid.uuid4().hex[:12].upper(); stamp=now(); fields={k:str(d.get(k,'')) for k in ('name','category','description','brand','color','location','date_event')}; private=str(d.get('private_details',''))
 digest=hashlib.sha256(json.dumps({'id':iid,'owner':g.user['id'],'kind':kind,**fields,'private':private},sort_keys=True).encode()).hexdigest(); c=db()
 c.execute('INSERT INTO items(id,owner_id,kind,name,category,description,brand,color,location,date_event,private_details,record_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(iid,g.user['id'],kind,name,category,fields['description'],fields['brand'],fields['color'],location,fields['date_event'],private,digest,stamp)); c.execute('INSERT INTO blockchain_transactions(item_id,type,status,created_at) VALUES(?,?,?,?)',(iid,'Item Registration','local_demo',stamp)); c.commit()
 return jsonify(itemId=iid,recordHash=digest,blockchainStatus='local_demo',transactionHash=None,message='Report saved locally. No blockchain transaction was submitted.'),201
@app.get('/api/items/<iid>')
def item(iid):
 r=db().execute('SELECT * FROM items WHERE id=?',(iid,)).fetchone(); return (jsonify(public(r)),200) if r else (jsonify(error='Item not found'),404)
@app.post('/api/items/<iid>/claims')
@auth()
def claim(iid):
 d=request.get_json() or {}; c=db(); item=c.execute('SELECT * FROM items WHERE id=?',(iid,)).fetchone()
 if not item or item['kind']!='found': return jsonify(error='Found item not available'),404
 if item['owner_id']==g.user['id']: return jsonify(error='Cannot claim your own report'),400
 if len(str(d.get('features','')).strip())<10: return jsonify(error='Describe identifying features (at least 10 characters)'),400
 cid='CL-'+uuid.uuid4().hex[:12].upper(); c.execute('INSERT INTO claims(id,item_id,user_id,features,purchase,created_at) VALUES(?,?,?,?,?,?)',(cid,iid,g.user['id'],d['features'],d.get('purchase',''),now())); c.execute("UPDATE items SET status='Claim Pending' WHERE id=?",(iid,)); c.commit(); return jsonify(claimId=cid,status='Pending'),201
@app.get('/api/claims')
@auth()
def claims():
 sql='SELECT c.*,i.name item_name FROM claims c JOIN items i ON i.id=c.item_id'; args=[]
 if g.user['role']!='admin': sql+=' WHERE c.user_id=?'; args=[g.user['id']]
 return jsonify([dict(r) for r in db().execute(sql,args)])
@app.post('/api/claims/<cid>/review')
@auth(True)
def review(cid):
 status=(request.get_json() or {}).get('status'); c=db()
 if status not in ('Approved','Rejected'): return jsonify(error='Status must be Approved or Rejected'),400
 r=c.execute('SELECT * FROM claims WHERE id=?',(cid,)).fetchone()
 if not r: return jsonify(error='Claim not found'),404
 c.execute('UPDATE claims SET status=?,reviewed_at=?,reviewer_id=? WHERE id=?',(status,now(),g.user['id'],cid)); c.execute('UPDATE items SET status=? WHERE id=?',('Approved' if status=='Approved' else 'Available',r['item_id'])); c.execute('INSERT INTO notifications(user_id,message,created_at) VALUES(?,?,?)',(r['user_id'],f'Claim {cid} {status.lower()}',now())); c.execute('INSERT INTO blockchain_transactions(item_id,type,status,created_at) VALUES(?,?,?,?)',(r['item_id'],'Claim Verification','local_demo',now())); c.commit(); return jsonify(status=status,blockchainStatus='local_demo',transactionHash=None)
@app.post('/api/claims/<cid>/handover')
@auth()
def handover(cid):
 c=db(); cl=c.execute('SELECT c.*,i.owner_id FROM claims c JOIN items i ON i.id=c.item_id WHERE c.id=?',(cid,)).fetchone()
 if not cl or cl['status']!='Approved': return jsonify(error='Approved claim required'),400
 if g.user['id'] not in (cl['owner_id'],cl['user_id']) and g.user['role']!='admin': return jsonify(error='Not authorized'),403
 h=c.execute('SELECT * FROM handovers WHERE claim_id=?',(cid,)).fetchone()
 if not h:
  hid='HO-'+uuid.uuid4().hex[:12].upper(); c.execute('INSERT INTO handovers(id,item_id,claim_id,created_at) VALUES(?,?,?,?)',(hid,cl['item_id'],cid,now())); h=c.execute('SELECT * FROM handovers WHERE id=?',(hid,)).fetchone()
 side='finder_confirmed' if g.user['id']==cl['owner_id'] else 'claimant_confirmed'; c.execute(f'UPDATE handovers SET {side}=1 WHERE id=?',(h['id'],)); h=c.execute('SELECT * FROM handovers WHERE id=?',(h['id'],)).fetchone(); done=h['finder_confirmed'] and h['claimant_confirmed']
 if done: c.execute("UPDATE items SET status='Returned' WHERE id=?",(cl['item_id'],)); c.execute("UPDATE handovers SET status='Returned' WHERE id=?",(h['id'],)); c.execute('INSERT INTO blockchain_transactions(item_id,type,status,created_at) VALUES(?,?,?,?)',(cl['item_id'],'Handover Confirmation','local_demo',now()))
 c.commit(); return jsonify(handoverId=h['id'],finderConfirmed=bool(h['finder_confirmed']),claimantConfirmed=bool(h['claimant_confirmed']),status='Returned' if done else 'Pending',blockchainStatus='local_demo' if done else None)
@app.get('/api/activity')
@auth()
def activity():
 c=db(); u=g.user['id']; return jsonify(reports=[public(r) for r in c.execute('SELECT * FROM items WHERE owner_id=?',(u,))],claims=[dict(r) for r in c.execute('SELECT c.*,i.name item_name FROM claims c JOIN items i ON i.id=c.item_id WHERE c.user_id=?',(u,))])
@app.get('/api/admin/overview')
@auth(True)
def overview():
 c=db(); return jsonify(users=[{k:r[k] for k in ('id','name','email','role')} for r in c.execute('SELECT * FROM users')],claims=[dict(r) for r in c.execute('SELECT c.*,u.name claimant,i.name item_name FROM claims c JOIN users u ON u.id=c.user_id JOIN items i ON i.id=c.item_id')],stats={'users':c.execute('SELECT count(*) FROM users').fetchone()[0],'items':c.execute('SELECT count(*) FROM items').fetchone()[0],'pendingClaims':c.execute("SELECT count(*) FROM claims WHERE status='Pending'").fetchone()[0]})
@app.get('/api/blockchain/transactions')
def transactions(): return jsonify([dict(r) for r in db().execute('SELECT * FROM blockchain_transactions ORDER BY created_at DESC')])
@app.get('/api/notifications')
@auth()
def notifications(): return jsonify([dict(r) for r in db().execute('SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC',(g.user['id'],))])
initialize()
if __name__=='__main__': app.run(port=int(os.getenv('PORT',5000)))
