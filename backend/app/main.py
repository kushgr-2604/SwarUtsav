"""SwarUtsav API: persistent MVP backend for interview preparation."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, sqlite3, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

APP_NAME = "SwarUtsav API"
API_PREFIX = os.getenv("API_V1_PREFIX", "/api/v1").rstrip("/")
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "./data/swarutsav.db"))
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-this-secret")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "86400"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

@contextmanager
def db():
    conn = sqlite3.connect(DATABASE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally: conn.close()

def now_iso(): return datetime.now(timezone.utc).isoformat()
def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'candidate',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS profiles(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,target_role TEXT NOT NULL DEFAULT '',education TEXT NOT NULL DEFAULT '',skills TEXT NOT NULL DEFAULT '[]',bio TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS interviews(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id),title TEXT NOT NULL,target_role TEXT NOT NULL,interview_type TEXT NOT NULL,difficulty TEXT NOT NULL,question_count INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'in_progress',created_at TEXT NOT NULL,completed_at TEXT);
        CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT NOT NULL,target_role TEXT NOT NULL,difficulty TEXT NOT NULL,prompt TEXT NOT NULL,keywords TEXT NOT NULL DEFAULT '[]',active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS responses(id INTEGER PRIMARY KEY AUTOINCREMENT,interview_id INTEGER NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,question_id INTEGER,question_text TEXT NOT NULL,answer_text TEXT NOT NULL,relevance REAL NOT NULL,completeness REAL NOT NULL,clarity REAL NOT NULL,feedback TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT,interview_id INTEGER NOT NULL UNIQUE REFERENCES interviews(id) ON DELETE CASCADE,overall_score REAL NOT NULL,summary TEXT NOT NULL,created_at TEXT NOT NULL);
        """)
        if conn.execute("SELECT COUNT(*) FROM questions").fetchone()[0] == 0:
            seeds=[
            ("Technical","Software Developer","beginner","Explain the difference between a list and a tuple in Python.",["list","tuple","mutable","immutable"]),
            ("Technical","Software Developer","intermediate","What is a REST API, and how would you design error handling for it?",["http","status code","validation","error"]),
            ("Technical","Software Developer","intermediate","Explain database indexing and one trade-off it introduces.",["index","query","read","write"]),
            ("Behavioural","Any","beginner","Tell me about a time you worked through a difficult problem.",["situation","action","result","learning"]),
            ("Behavioural","Any","intermediate","Describe a disagreement in a team and how you handled it.",["listen","evidence","collaborate","outcome"]),
            ("HR","Any","beginner","Why are you interested in this role?",["motivation","skills","role","growth"])]
            conn.executemany("INSERT INTO questions(category,target_role,difficulty,prompt,keywords) VALUES(?,?,?,?,?)",[(c,r,d,p,json.dumps(k)) for c,r,d,p,k in seeds])

def b64url(raw: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
def issue_token(user_id: int, role: str) -> str:
    header=b64url(json.dumps({"alg":"HS256","typ":"JWT"},separators=(",",":")).encode())
    payload=b64url(json.dumps({"sub":str(user_id),"role":role,"exp":int(time.time())+TOKEN_TTL_SECONDS},separators=(",",":")).encode())
    body=f"{header}.{payload}"
    return f"{body}.{b64url(hmac.new(JWT_SECRET.encode(),body.encode(),hashlib.sha256).digest())}"
def decode_token(token: str):
    import base64
    try:
        header,payload,signature=token.split(".")
        expected=b64url(hmac.new(JWT_SECRET.encode(),f"{header}.{payload}".encode(),hashlib.sha256).digest())
        if not hmac.compare_digest(signature,expected): raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(payload+"="*(-len(payload)%4)))
        if int(data["exp"]) < int(time.time()): raise ValueError()
        return data
    except Exception: raise HTTPException(status_code=401,detail="Invalid or expired access token")
def current_user(authorization: Optional[str]=Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(status_code=401,detail="Bearer token required")
    token=decode_token(authorization[7:])
    with db() as conn: row=conn.execute("SELECT id,name,email,role FROM users WHERE id=?",(int(token["sub"]),)).fetchone()
    if not row: raise HTTPException(status_code=401,detail="User no longer exists")
    return dict(row)
def require_admin(user=Depends(current_user)):
    if user["role"]!="admin": raise HTTPException(status_code=403,detail="Administrator access required")
    return user

class RegisterInput(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    email:EmailStr
    password:str=Field(min_length=8,max_length=128)
class LoginInput(BaseModel):
    email:EmailStr
    password:str
class ProfileInput(BaseModel):
    target_role:str=Field(default="",max_length=120)
    education:str=Field(default="",max_length=200)
    skills:list[str]=Field(default_factory=list,max_length=40)
    bio:str=Field(default="",max_length=1000)
class InterviewInput(BaseModel):
    title:str=Field(default="Practice interview",min_length=2,max_length=160)
    target_role:str=Field(min_length=2,max_length=120)
    interview_type:str=Field(default="Technical",pattern="^(Technical|Behavioural|HR|Mixed)$")
    difficulty:str=Field(default="intermediate",pattern="^(beginner|intermediate|advanced)$")
    question_count:int=Field(default=5,ge=1,le=20)
class AnswerInput(BaseModel):
    question_id:Optional[int]=None
    question_text:str=Field(min_length=5,max_length=2000)
    answer_text:str=Field(min_length=1,max_length=12000)

app=FastAPI(title=APP_NAME,version="1.0.0",description="REST API for SwarUtsav AI interview preparation portal.")
app.add_middleware(CORSMiddleware,allow_origins=list({FRONTEND_URL,"http://localhost:3000","http://127.0.0.1:3000"}),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
init_db()

@app.get("/health",tags=["system"])
@app.get(f"{API_PREFIX}/health",tags=["system"])
def health(): return {"status":"ok","service":"swarutsav-api","timestamp":now_iso()}

@app.post(f"{API_PREFIX}/auth/register",status_code=201,tags=["auth"])
def register(payload:RegisterInput):
    salt=secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac("sha256",payload.password.encode(),salt,310000)
    encoded=salt.hex()+"$"+digest.hex()
    try:
        with db() as conn:
            user_id=conn.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(payload.name.strip(),payload.email.lower(),encoded,now_iso())).lastrowid
            conn.execute("INSERT INTO profiles(user_id) VALUES(?)",(user_id,))
    except sqlite3.IntegrityError: raise HTTPException(status_code=409,detail="An account with this email already exists")
    return {"access_token":issue_token(user_id,"candidate"),"token_type":"bearer","user":{"id":user_id,"name":payload.name.strip(),"email":payload.email.lower(),"role":"candidate"}}

@app.post(f"{API_PREFIX}/auth/login",tags=["auth"])
def login(payload:LoginInput):
    with db() as conn: user=conn.execute("SELECT * FROM users WHERE email=?",(payload.email.lower(),)).fetchone()
    if not user: raise HTTPException(status_code=401,detail="Incorrect email or password")
    try:
        salt,digest=user["password_hash"].split("$",1)
        actual=hashlib.pbkdf2_hmac("sha256",payload.password.encode(),bytes.fromhex(salt),310000).hex()
    except Exception: actual=""; digest="invalid"
    if not hmac.compare_digest(actual,digest): raise HTTPException(status_code=401,detail="Incorrect email or password")
    return {"access_token":issue_token(user["id"],user["role"]),"token_type":"bearer","user":{"id":user["id"],"name":user["name"],"email":user["email"],"role":user["role"]}}

@app.get(f"{API_PREFIX}/auth/me",tags=["auth"])
def me(user=Depends(current_user)): return user

@app.get(f"{API_PREFIX}/profile",tags=["profile"])
def get_profile(user=Depends(current_user)):
    with db() as conn: row=conn.execute("SELECT target_role,education,skills,bio FROM profiles WHERE user_id=?",(user["id"],)).fetchone()
    result=dict(row) if row else {"target_role":"","education":"","skills":"[]","bio":""}
    result["skills"]=json.loads(result["skills"]); return result
@app.put(f"{API_PREFIX}/profile",tags=["profile"])
def update_profile(payload:ProfileInput,user=Depends(current_user)):
    with db() as conn: conn.execute("INSERT INTO profiles(user_id,target_role,education,skills,bio) VALUES(?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET target_role=excluded.target_role,education=excluded.education,skills=excluded.skills,bio=excluded.bio",(user["id"],payload.target_role,payload.education,json.dumps(payload.skills),payload.bio))
    return payload.model_dump()

@app.get(f"{API_PREFIX}/questions",tags=["questions"])
def list_questions(category:Optional[str]=None,difficulty:Optional[str]=None,limit:int=50,user=Depends(current_user)):
    limit=max(1,min(limit,100)); sql="SELECT id,category,target_role,difficulty,prompt,keywords FROM questions WHERE active=1"; args=[]
    if category: sql+=" AND category=?"; args.append(category)
    if difficulty: sql+=" AND difficulty=?"; args.append(difficulty)
    sql+=" ORDER BY id LIMIT ?"; args.append(limit)
    with db() as conn: rows=conn.execute(sql,args).fetchall()
    return [{**dict(r),"keywords":json.loads(r["keywords"])} for r in rows]

@app.post(f"{API_PREFIX}/interviews",status_code=201,tags=["interviews"])
def create_interview(payload:InterviewInput,user=Depends(current_user)):
    with db() as conn:
        iid=conn.execute("INSERT INTO interviews(user_id,title,target_role,interview_type,difficulty,question_count,created_at) VALUES(?,?,?,?,?,?,?)",(user["id"],payload.title,payload.target_role,payload.interview_type,payload.difficulty,payload.question_count,now_iso())).lastrowid
        filters=["active=1"]; args=[]
        if payload.interview_type!="Mixed": filters.append("category=?"); args.append(payload.interview_type)
        filters.append("(target_role=? OR target_role='Any')"); args.append(payload.target_role)
        filters.append("difficulty=?"); args.append(payload.difficulty)
        questions=conn.execute("SELECT id,category,prompt FROM questions WHERE "+" AND ".join(filters)+" ORDER BY RANDOM() LIMIT ?",(*args,payload.question_count)).fetchall()
        if len(questions)<payload.question_count:
            extra=conn.execute("SELECT id,category,prompt FROM questions WHERE active=1 ORDER BY RANDOM() LIMIT ?",(payload.question_count-len(questions),)).fetchall()
            seen={q["id"] for q in questions}; questions=list(questions)+[q for q in extra if q["id"] not in seen]
    return {"id":iid,"title":payload.title,"target_role":payload.target_role,"interview_type":payload.interview_type,"difficulty":payload.difficulty,"question_count":payload.question_count,"status":"in_progress","questions":[dict(q) for q in questions]}

@app.get(f"{API_PREFIX}/interviews",tags=["interviews"])
def list_interviews(user=Depends(current_user)):
    with db() as conn: rows=conn.execute("SELECT i.*,r.overall_score FROM interviews i LEFT JOIN reports r ON r.interview_id=i.id WHERE i.user_id=? ORDER BY i.id DESC",(user["id"],)).fetchall()
    return [dict(r) for r in rows]
@app.get(f"{API_PREFIX}/interviews/{{interview_id}}",tags=["interviews"])
def get_interview(interview_id:int,user=Depends(current_user)):
    with db() as conn:
        interview=conn.execute("SELECT * FROM interviews WHERE id=? AND user_id=?",(interview_id,user["id"])).fetchone()
        if not interview: raise HTTPException(status_code=404,detail="Interview not found")
        responses=conn.execute("SELECT id,question_id,question_text,answer_text,relevance,completeness,clarity,feedback,created_at FROM responses WHERE interview_id=? ORDER BY id",(interview_id,)).fetchall()
    return {**dict(interview),"responses":[dict(r) for r in responses]}

def evaluate_answer(question:str,answer:str):
    """Transparent baseline rubric; replace with an approved external LLM evaluator later."""
    words=answer.strip().split()
    qterms={w.lower().strip(".,?!:;()") for w in question.split() if len(w)>4}
    aterms={w.lower().strip(".,?!:;()") for w in answer.split() if len(w)>4}
    overlap=len(qterms & aterms)/max(1,len(qterms))
    relevance=round(min(95,45+overlap*50),1); completeness=round(min(95,len(words)/80*100),1); clarity=round(min(95,55+min(len(words),100)*.35),1)
    tips=[]
    if len(words)<35: tips.append("Add detail and support your answer with a concrete example.")
    if overlap<.15: tips.append("Address key terms and concepts in the question more directly.")
    if not tips: tips.append("Strengthen the answer with evidence, trade-offs, or a measurable result.")
    return {"relevance":relevance,"completeness":completeness,"clarity":clarity,"overall":round(relevance*.5+completeness*.3+clarity*.2,1),"feedback":" ".join(tips),"evaluation_method":"transparent_baseline_rubric"}

@app.post(f"{API_PREFIX}/interviews/{{interview_id}}/answers",status_code=201,tags=["interviews"])
def submit_answer(interview_id:int,payload:AnswerInput,user=Depends(current_user)):
    scores=evaluate_answer(payload.question_text,payload.answer_text)
    with db() as conn:
        interview=conn.execute("SELECT id,status FROM interviews WHERE id=? AND user_id=?",(interview_id,user["id"])).fetchone()
        if not interview: raise HTTPException(status_code=404,detail="Interview not found")
        if interview["status"]!="in_progress": raise HTTPException(status_code=409,detail="Interview is already completed")
        conn.execute("INSERT INTO responses(interview_id,question_id,question_text,answer_text,relevance,completeness,clarity,feedback,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(interview_id,payload.question_id,payload.question_text,payload.answer_text,scores["relevance"],scores["completeness"],scores["clarity"],scores["feedback"],now_iso()))
    return scores

@app.post(f"{API_PREFIX}/interviews/{{interview_id}}/complete",tags=["interviews"])
def complete_interview(interview_id:int,user=Depends(current_user)):
    with db() as conn:
        interview=conn.execute("SELECT id,status FROM interviews WHERE id=? AND user_id=?",(interview_id,user["id"])).fetchone()
        if not interview: raise HTTPException(status_code=404,detail="Interview not found")
        rows=conn.execute("SELECT relevance,completeness,clarity,feedback FROM responses WHERE interview_id=?",(interview_id,)).fetchall()
        if not rows: raise HTTPException(status_code=400,detail="Submit at least one answer before completing the interview")
        overall=round(sum(r["relevance"]*.5+r["completeness"]*.3+r["clarity"]*.2 for r in rows)/len(rows),1)
        summary=" ".join(dict.fromkeys(r["feedback"] for r in rows))
        conn.execute("UPDATE interviews SET status='completed',completed_at=? WHERE id=?",(now_iso(),interview_id))
        conn.execute("INSERT INTO reports(interview_id,overall_score,summary,created_at) VALUES(?,?,?,?) ON CONFLICT(interview_id) DO UPDATE SET overall_score=excluded.overall_score,summary=excluded.summary,created_at=excluded.created_at",(interview_id,overall,summary,now_iso()))
    return {"interview_id":interview_id,"overall_score":overall,"responses_count":len(rows),"summary":summary,"note":"Scores use the built-in baseline rubric, not an LLM assessment."}

@app.get(f"{API_PREFIX}/reports",tags=["reports"])
def list_reports(user=Depends(current_user)):
    with db() as conn: rows=conn.execute("SELECT r.id,r.interview_id,r.overall_score,r.summary,r.created_at,i.title,i.target_role FROM reports r JOIN interviews i ON i.id=r.interview_id WHERE i.user_id=? ORDER BY r.id DESC",(user["id"],)).fetchall()
    return [dict(r) for r in rows]
@app.get(f"{API_PREFIX}/reports/{{interview_id}}",tags=["reports"])
def get_report(interview_id:int,user=Depends(current_user)):
    with db() as conn:
        row=conn.execute("SELECT r.*,i.title,i.target_role,i.interview_type,i.difficulty FROM reports r JOIN interviews i ON i.id=r.interview_id WHERE r.interview_id=? AND i.user_id=?",(interview_id,user["id"])).fetchone()
        responses=conn.execute("SELECT question_text,answer_text,relevance,completeness,clarity,feedback FROM responses WHERE interview_id=? ORDER BY id",(interview_id,)).fetchall()
    if not row: raise HTTPException(status_code=404,detail="Report not found; complete an interview first")
    return {**dict(row),"responses":[dict(r) for r in responses],"evaluation_method":"transparent_baseline_rubric"}

@app.get(f"{API_PREFIX}/admin/overview",tags=["admin"])
def admin_overview(user=Depends(require_admin)):
    with db() as conn:
        return {"users":conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],"interviews":conn.execute("SELECT COUNT(*) FROM interviews").fetchone()[0],"completed_interviews":conn.execute("SELECT COUNT(*) FROM interviews WHERE status='completed'").fetchone()[0],"questions":conn.execute("SELECT COUNT(*) FROM questions WHERE active=1").fetchone()[0]}
