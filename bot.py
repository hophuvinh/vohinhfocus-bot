import os
import json
import logging
import re
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
DATA_FILE = "tasks.json"
PORT = int(os.environ.get("PORT", 8080))

# ===== DATA =====
def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def next_id(tasks):
    return max((t["id"] for t in tasks), default=0) + 1

# ===== WEB APP HTML =====
WEB_APP_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0">
<title>FocusFlow</title>
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Bricolage+Grotesque:wght@400;500;600;800&display=swap" rel="stylesheet">
<style>
:root{--bg:#f5f2ec;--surface:#fff;--surface2:#edeae3;--border:#ddd9d0;--text:#1a1815;--muted:#8a8680;--accent:#d4521a;}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent;}
body{background:var(--bg);color:var(--text);font-family:"Bricolage Grotesque",sans-serif;min-height:100vh;padding-bottom:80px;}
.bottom-nav{position:fixed;bottom:0;left:0;right:0;background:var(--surface);border-top:1px solid var(--border);display:flex;z-index:100;padding-bottom:env(safe-area-inset-bottom);}
.nav-item{flex:1;display:flex;flex-direction:column;align-items:center;padding:10px 0 8px;gap:3px;cursor:pointer;font-size:10px;font-weight:600;color:var(--muted);letter-spacing:.5px;text-transform:uppercase;border:none;background:transparent;transition:color .15s;}
.nav-item.active{color:var(--accent);}
.nav-icon{font-size:20px;line-height:1;}
.view{display:none;padding:16px;animation:fadeIn .2s ease;}
.view.active{display:block;}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
.view-title{font-size:20px;font-weight:800;letter-spacing:-.5px;margin-bottom:2px;}
.view-sub{font-size:12px;color:var(--muted);font-family:"DM Mono",monospace;margin-bottom:16px;}
.stats-row{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:14px;display:flex;align-items:center;gap:10px;}
.stat-icon{font-size:22px;}
.stat-num{font-family:"DM Mono",monospace;font-size:24px;font-weight:500;line-height:1;}
.stat-label{font-size:11px;color:var(--muted);}
.section{margin-bottom:20px;}
.section-label{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:10px;display:flex;align-items:center;gap:8px;}
.section-label::after{content:"";flex:1;height:1px;background:var(--border);}
.task-card{display:flex;align-items:flex-start;gap:10px;padding:12px 14px;border-radius:10px;border:1px solid var(--border);margin-bottom:8px;background:var(--surface);}
.task-card.done{opacity:.4;}
.task-check{width:20px;height:20px;border-radius:6px;border:1.5px solid var(--border);flex-shrink:0;margin-top:1px;display:flex;align-items:center;justify-content:center;background:var(--bg);cursor:pointer;font-size:12px;font-weight:700;}
.task-check.checked{background:var(--accent);border-color:var(--accent);color:white;}
.task-info{flex:1;min-width:0;}
.task-name{font-size:14px;font-weight:500;line-height:1.3;margin-bottom:5px;}
.task-card.done .task-name{text-decoration:line-through;}
.task-meta{display:flex;gap:5px;flex-wrap:wrap;align-items:center;}
.tag{font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;letter-spacing:.3px;text-transform:uppercase;}
.tag-kv{background:#fde8dc;color:#d4521a;}.tag-uiux{background:#dceeff;color:#1a3a6b;}.tag-hr{background:#dcf0e4;color:#2d5a3d;}.tag-feedback{background:#f0e4f5;color:#7a2d5a;}.tag-boss{background:#1a1815;color:#f5f2ec;}
.source-tag{font-family:"DM Mono",monospace;font-size:10px;color:var(--muted);}
.deadline-tag{font-family:"DM Mono",monospace;font-size:10px;color:var(--muted);margin-left:auto;}
.deadline-urgent{color:#d4521a;font-weight:700;}
.move-row{display:flex;gap:6px;margin-top:8px;}
.move-btn{padding:4px 10px;border-radius:6px;border:1px solid var(--border);font-family:"Bricolage Grotesque",sans-serif;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg);color:var(--muted);}
.move-btn.active{background:var(--text);color:var(--bg);border-color:var(--text);}
.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:40px 20px;color:var(--muted);font-size:13px;gap:8px;text-align:center;}
.empty-icon{font-size:32px;opacity:.4;}
.week-col{margin-bottom:16px;}
.week-day-header{display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-radius:8px;margin-bottom:6px;background:var(--surface2);font-size:12px;font-weight:700;}
.week-day-header.today{background:var(--accent);color:white;}
.week-day-date{font-family:"DM Mono",monospace;font-size:11px;opacity:.7;}
.focus-wrap{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:70vh;text-align:center;padding:20px;}
.focus-tag{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:16px;}
.focus-task{font-size:22px;font-weight:700;line-height:1.3;margin-bottom:40px;max-width:280px;}
.focus-timer{font-family:"DM Mono",monospace;font-size:72px;font-weight:400;color:var(--accent);line-height:1;margin-bottom:32px;letter-spacing:-2px;}
.focus-btns{display:flex;gap:12px;margin-bottom:24px;}
.focus-btn{padding:12px 28px;border-radius:10px;border:none;font-family:"Bricolage Grotesque",sans-serif;font-size:14px;font-weight:700;cursor:pointer;}
.btn-start{background:var(--accent);color:white;}.btn-reset{background:var(--surface2);color:var(--muted);}
.focus-progress{width:100%;max-width:300px;height:3px;background:var(--border);border-radius:2px;overflow:hidden;}
.focus-fill{height:100%;background:var(--accent);border-radius:2px;transition:width 1s linear;}
.focus-select{width:100%;max-width:340px;background:var(--surface);border:1px solid var(--border);border-radius:12px;overflow:hidden;}
.focus-task-option{padding:12px 16px;display:flex;align-items:center;gap:10px;cursor:pointer;border-bottom:1px solid var(--border);}
.focus-task-option:last-child{border-bottom:none;}
.focus-task-option-name{font-size:13px;font-weight:500;}
</style>
</head>
<body>
<div id="view-daily" class="view active">
  <div class="view-title">Hôm nay</div>
  <div class="view-sub" id="dateStr"></div>
  <div class="stats-row" id="statsRow"></div>
  <div class="section"><div class="section-label">🎯 Deep Focus</div><div id="focusList"></div></div>
  <div class="section"><div class="section-label">⚡ Reactive</div><div id="reactiveList"></div></div>
</div>
<div id="view-inbox" class="view">
  <div class="view-title">Inbox</div>
  <div class="view-sub">Chưa assign</div>
  <div id="inboxList"></div>
</div>
<div id="view-weekly" class="view">
  <div class="view-title">Tuần này</div>
  <div class="view-sub" id="weekRange"></div>
  <div id="weekList"></div>
</div>
<div id="view-focus" class="view">
  <div id="focusModeWrap"></div>
</div>
<nav class="bottom-nav">
  <button class="nav-item active" onclick="switchView('daily',this)"><span class="nav-icon">📅</span>Hôm nay</button>
  <button class="nav-item" onclick="switchView('inbox',this)"><span class="nav-icon">📥</span>Inbox</button>
  <button class="nav-item" onclick="switchView('weekly',this)"><span class="nav-icon">📆</span>Tuần</button>
  <button class="nav-item" onclick="switchView('focus',this)"><span class="nav-icon">🎯</span>Focus</button>
</nav>
<script>
const tg=window.Telegram?.WebApp;if(tg){tg.ready();tg.expand();}
const TL={kv:"KV/Branding",uiux:"UI/UX",hr:"HR/Quy trình",feedback:"Feedback",boss:"Từ sếp"};
const SL={editorial:"Editorial",sales:"Sales",boss:"Sếp",client:"Khách",self:"Cá nhân"};
let tasks=[],timerInterval=null,timerSeconds=1500,timerRunning=false,totalSeconds=1500,currentFocusTask=null;
async function loadTasks(){try{const r=await fetch('/api/tasks');tasks=await r.json();render();}catch(e){}}
async function updateTask(id,changes){await fetch('/api/tasks/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(changes)});await loadTasks();}
function getTodayStr(){return new Date().toISOString().split('T')[0];}
function formatDate(s){if(!s)return'';const d=new Date(s+'T00:00:00');return d.getDate()+'/'+(d.getMonth()+1);}
function isUrgent(dl){return dl&&dl<=getTodayStr();}
function taskCard(t,showMove=false){
  const u=isUrgent(t.deadline)&&!t.done;
  return `<div class="task-card ${t.done?'done':''}">
    <div class="task-check ${t.done?'checked':''}" onclick="toggleDone(${t.id})">${t.done?'✓':''}</div>
    <div class="task-info">
      <div class="task-name">${t.name}</div>
      <div class="task-meta">
        <span class="tag tag-${t.type}">${TL[t.type]||t.type}</span>
        <span class="source-tag">${SL[t.source]||t.source}</span>
        ${t.deadline?`<span class="deadline-tag ${u?'deadline-urgent':''}">${u?'🔴 ':''}${formatDate(t.deadline)}</span>`:''}
      </div>
      ${showMove?`<div class="move-row">
        <button class="move-btn ${t.today==='focus'?'active':''}" onclick="moveTo(${t.id},'focus')">🎯 Focus</button>
        <button class="move-btn ${t.today==='reactive'?'active':''}" onclick="moveTo(${t.id},'reactive')">⚡ Reactive</button>
      </div>`:''}
    </div>
  </div>`;}
function render(){
  const now=new Date();
  document.getElementById('dateStr').textContent=now.toLocaleDateString('vi-VN',{weekday:'long',day:'2-digit',month:'2-digit',year:'numeric'});
  const focus=tasks.filter(t=>t.today==='focus'&&!t.done);
  const reactive=tasks.filter(t=>t.today==='reactive'&&!t.done);
  const inbox=tasks.filter(t=>t.today==='inbox'&&!t.done);
  const done=tasks.filter(t=>t.done);
  document.getElementById('statsRow').innerHTML=`
    <div class="stat-card"><span class="stat-icon">🎯</span><div><div class="stat-num">${focus.length}</div><div class="stat-label">Deep focus</div></div></div>
    <div class="stat-card"><span class="stat-icon">✅</span><div><div class="stat-num">${done.length}</div><div class="stat-label">Hoàn thành</div></div></div>`;
  document.getElementById('focusList').innerHTML=focus.length?focus.map(t=>taskCard(t)).join(''):'<div class="empty"><div class="empty-icon">🎯</div>Chưa có task deep focus</div>';
  document.getElementById('reactiveList').innerHTML=reactive.length?reactive.map(t=>taskCard(t)).join(''):'<div class="empty"><div class="empty-icon">⚡</div>Không có task reactive</div>';
  document.getElementById('inboxList').innerHTML=inbox.length?inbox.map(t=>taskCard(t,true)).join(''):'<div class="empty"><div class="empty-icon">📥</div>Inbox trống 🎉</div>';
  renderWeek();
  if(!currentFocusTask)renderFocusSelect();
}
function renderWeek(){
  const today=new Date(),monday=new Date(today);
  monday.setDate(today.getDate()-today.getDay()+(today.getDay()===0?-6:1));
  const days=['T2','T3','T4','T5','T6','T7','CN'];
  const sunday=new Date(monday);sunday.setDate(monday.getDate()+6);
  document.getElementById('weekRange').textContent=monday.getDate()+'/'+(monday.getMonth()+1)+' – '+sunday.getDate()+'/'+(sunday.getMonth()+1);
  let html='';
  for(let i=0;i<7;i++){
    const d=new Date(monday);d.setDate(monday.getDate()+i);
    const ds=d.toISOString().split('T')[0],isToday=ds===today.toISOString().split('T')[0];
    const dt=tasks.filter(t=>t.deadline===ds&&!t.done);
    html+=`<div class="week-col"><div class="week-day-header ${isToday?'today':''}"><span>${days[i]}</span><span class="week-day-date">${d.getDate()}/${d.getMonth()+1}${isToday?' — hôm nay':''}</span></div>${dt.length?dt.map(t=>taskCard(t)).join(''):'<div style="color:var(--muted);font-size:12px;padding:6px 4px">Trống</div>'}</div>`;
  }
  document.getElementById('weekList').innerHTML=html;
}
function renderFocusSelect(){
  const ft=tasks.filter(t=>t.today==='focus'&&!t.done);
  document.getElementById('focusModeWrap').innerHTML=ft.length?
    `<div class="focus-wrap"><div class="focus-tag">CHỌN TASK ĐỂ BẮT ĐẦU</div><div class="focus-select">${ft.map(t=>`<div class="focus-task-option" onclick="startFocus(${t.id})"><span class="tag tag-${t.type}">${TL[t.type]}</span><span class="focus-task-option-name">${t.name}</span></div>`).join('')}</div></div>`:
    `<div class="focus-wrap"><div class="empty-icon">🎯</div><div style="margin-top:12px;color:var(--muted);font-size:14px">Chưa có task deep focus.<br>Thêm qua Telegram bot nhé!</div></div>`;
}
function startFocus(id){
  currentFocusTask=tasks.find(t=>t.id===id);
  timerSeconds=1500;totalSeconds=1500;timerRunning=false;clearInterval(timerInterval);
  document.getElementById('focusModeWrap').innerHTML=`<div class="focus-wrap">
    <div class="focus-tag">${TL[currentFocusTask.type]}</div>
    <div class="focus-task">${currentFocusTask.name}</div>
    <div class="focus-timer" id="td">25:00</div>
    <div class="focus-btns">
      <button class="focus-btn btn-start" id="sb" onclick="toggleTimer()">▶ Bắt đầu</button>
      <button class="focus-btn btn-reset" onclick="resetTimer()">↺ Reset</button>
    </div>
    <div class="focus-progress"><div class="focus-fill" id="tf" style="width:0%"></div></div>
    <div style="margin-top:20px"><button class="move-btn" onclick="currentFocusTask=null;clearInterval(timerInterval);timerRunning=false;renderFocusSelect()">← Chọn task khác</button></div>
  </div>`;}
function toggleTimer(){
  const btn=document.getElementById('sb');
  if(timerRunning){clearInterval(timerInterval);timerRunning=false;btn.textContent='▶ Tiếp tục';}
  else{timerRunning=true;btn.textContent='⏸ Tạm dừng';
    timerInterval=setInterval(()=>{
      timerSeconds--;
      if(timerSeconds<=0){clearInterval(timerInterval);timerRunning=false;document.getElementById('td').textContent='00:00';document.getElementById('tf').style.width='100%';document.getElementById('sb').textContent='✓ Xong!';toggleDone(currentFocusTask.id);currentFocusTask=null;return;}
      const m=Math.floor(timerSeconds/60),s=timerSeconds%60;
      document.getElementById('td').textContent=String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
      document.getElementById('tf').style.width=((totalSeconds-timerSeconds)/totalSeconds*100)+'%';
    },1000);}
}
function resetTimer(){clearInterval(timerInterval);timerRunning=false;timerSeconds=1500;document.getElementById('td').textContent='25:00';document.getElementById('tf').style.width='0%';document.getElementById('sb').textContent='▶ Bắt đầu';}
async function toggleDone(id){const t=tasks.find(t=>t.id===id);if(t)await updateTask(id,{done:!t.done});}
async function moveTo(id,slot){
  if(slot==='focus'&&tasks.filter(t=>t.today==='focus'&&!t.done&&t.id!==id).length>=3){alert('Tối đa 3 task Deep Focus!');return;}
  await updateTask(id,{today:slot});
}
function switchView(name,btn){
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.remove('active'));
  document.getElementById('view-'+name).classList.add('active');btn.classList.add('active');
}
loadTasks();setInterval(loadTasks,30000);
</script>
</body>
</html>"""

# ===== WEB SERVER =====
class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def do_GET(self):
        if self.path in ['/', '/app']:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(WEB_APP_HTML.encode('utf-8'))
        elif self.path == '/api/tasks':
            data = json.dumps(load_tasks(), ensure_ascii=False)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data.encode('utf-8'))
        else:
            self.send_response(404); self.end_headers()

    def do_PATCH(self):
        if self.path.startswith('/api/tasks/'):
            task_id = int(self.path.split('/')[-1])
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            tasks = load_tasks()
            task = next((t for t in tasks if t['id'] == task_id), None)
            if task:
                task.update(body); save_tasks(tasks)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(task, ensure_ascii=False).encode())
            else:
                self.send_response(404); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

def run_web_server():
    server = HTTPServer(('0.0.0.0', PORT), RequestHandler)
    logger.info(f"Web server on port {PORT}")
    server.serve_forever()

# ===== NLP =====
TYPE_KEYWORDS = {
    "kv": ["kv","key visual","concept","branding","brand","logo","nhận diện"],
    "uiux": ["ui","ux","giao diện","interface","trang","web","layout","wireframe"],
    "hr": ["nhân sự","quy trình","hr","team","tuyển","onboard","cải tiến","improve"],
    "feedback": ["feedback","review","approve","duyệt","check","sửa","chỉnh"],
    "boss": ["sếp","boss","anh","chị giao","yêu cầu gấp"],
}
SOURCE_KEYWORDS = {
    "editorial": ["editorial","biên tập","ban biên","trang tin","news","bài"],
    "sales": ["sales","kinh doanh","khách chốt","chốt tiền","proposal"],
    "boss": ["sếp","boss","giám đốc"],
    "client": ["khách hàng","client","agency","đối tác","samsung","honda"],
    "self": ["cá nhân","tự làm","mình cần"],
}
URGENCY_PATTERNS = [
    (r"hôm nay|today|ngay bây giờ|gấp|urgent", 0),
    (r"ngày mai|tomorrow|mai", 1),
    (r"tuần này|this week", 3),
    (r"(\d+)\s*ngày", None),
]

def parse_task(text):
    tl = text.lower()
    task_type = next((t for t, kws in TYPE_KEYWORDS.items() if any(k in tl for k in kws)), "kv")
    source = next((s for s, kws in SOURCE_KEYWORDS.items() if any(k in tl for k in kws)), "self")
    deadline = None
    today = datetime.now()
    for pattern, delta in URGENCY_PATTERNS:
        m = re.search(pattern, tl)
        if m:
            days = int(m.group(1)) if delta is None else delta
            deadline = (today + timedelta(days=days)).strftime("%Y-%m-%d")
            break
    if not deadline: deadline = today.strftime("%Y-%m-%d")
    today_slot = "focus" if task_type in ["kv","uiux","hr"] else "reactive"
    name = text.strip()
    for f in ["hôm nay cần làm","cần làm","hôm nay","tôi cần","mình cần"]:
        if name.lower().startswith(f): name = name[len(f):].strip(); break
    name = name[:1].upper()+name[1:] if name else text
    return {"type":task_type,"source":source,"deadline":deadline,"today":today_slot,"name":name}

TYPE_LABELS = {"kv":"KV/Branding","uiux":"UI/UX","hr":"HR/Quy trình","feedback":"Feedback","boss":"Từ sếp"}
SOURCE_LABELS = {"editorial":"Editorial","sales":"Sales","boss":"Sếp","client":"Khách hàng","self":"Cá nhân"}
TODAY_LABELS = {"focus":"🎯 Deep Focus","reactive":"⚡ Reactive","inbox":"📥 Inbox"}
DONE_KW = ["xong","done","hoàn thành","xong rồi","làm xong","ok xong","finish","completed","xog"]

def is_done(text): return any(k in text.lower() for k in DONE_KW)

def similarity(a, b):
    a,b = a.lower(),b.lower()
    if a==b: return 1.0
    wa,wb = set(a.split()),set(b.split())
    if not wa or not wb: return 0.0
    return len(wa&wb)/max(len(wa),len(wb))

def find_dup(name, tasks):
    return next((t for t in tasks if not t.get("done") and similarity(name,t["name"])>=0.7), None)

def get_webapp_url():
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_STATIC_URL")
    return f"https://{domain}/app" if domain else None

# ===== BOT HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = get_webapp_url()
    kb = [[InlineKeyboardButton("📋 Mở FocusFlow", web_app=WebAppInfo(url=url))]] if url else []
    await update.message.reply_text(
        "👋 Chào Vinh!\n\nNhắn tự nhiên để thêm task:\n\n"
        "💬 *Ví dụ:*\n• _Hôm nay làm KV cho Better Choice_\n• _Feedback banner editorial gấp_\n• _Sếp giao proposal Samsung ngày mai_\n\n"
        "📋 /today /inbox /week /done /app",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb) if kb else None)

async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = get_webapp_url()
    if not url:
        await update.message.reply_text("⚠️ Cần set RAILWAY_PUBLIC_DOMAIN trong Variables")
        return
    await update.message.reply_text("Mở FocusFlow 👇",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 FocusFlow", web_app=WebAppInfo(url=url))]]))

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks(); url = get_webapp_url()
    focus = [t for t in tasks if t.get("today")=="focus" and not t.get("done")]
    reactive = [t for t in tasks if t.get("today")=="reactive" and not t.get("done")]
    done = [t for t in tasks if t.get("done")]
    msg = f"📅 *{datetime.now().strftime('%d/%m/%Y')}*\n\n🎯 *Focus ({len(focus)}/3)*\n"
    msg += "".join(f"  • {t['name']}\n" for t in focus) or "  _Chưa có_\n"
    msg += f"\n⚡ *Reactive ({len(reactive)})*\n"
    msg += "".join(f"  • {t['name']}\n" for t in reactive) or "  _Trống_\n"
    if done: msg += f"\n✅ *Xong ({len(done)})*\n" + "".join(f"  ~~{t['name']}~~\n" for t in done[-3:])
    kb = [[InlineKeyboardButton("📋 Xem FocusFlow", web_app=WebAppInfo(url=url))]] if url else []
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb) if kb else None)

async def inbox_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks(); url = get_webapp_url()
    inbox = [t for t in tasks if t.get("today")=="inbox" and not t.get("done")]
    if not inbox:
        await update.message.reply_text("📥 Inbox trống 🎉"); return
    msg = f"📥 *Inbox ({len(inbox)})*\n\n"
    for t in inbox:
        dl = f" — {datetime.strptime(t['deadline'],'%Y-%m-%d').strftime('%d/%m')}" if t.get("deadline") else ""
        msg += f"• [{t['id']}] {t['name']}{dl}\n"
    msg += "\n_/move [id] focus để assign_"
    kb = [[InlineKeyboardButton("📋 Xem FocusFlow", web_app=WebAppInfo(url=url))]] if url else []
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb) if kb else None)

async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks(); today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    days_vi = ["T2","T3","T4","T5","T6","T7","CN"]
    msg = "📆 *Tuần này*\n\n"
    for i in range(7):
        day = monday + timedelta(days=i); ds = day.strftime("%Y-%m-%d")
        dt = [t for t in tasks if t.get("deadline")==ds and not t.get("done")]
        is_today = ds==today.strftime("%Y-%m-%d")
        if dt or is_today:
            msg += f"*{days_vi[i]} {day.strftime('%d/%m')}*{' ◀' if is_today else ''}\n"
            msg += "".join(f"  • {t['name']}\n" for t in dt) or "  _Trống_\n"
            msg += "\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_tasks()
    active = [t for t in tasks if not t.get("done") and t.get("today") in ["focus","reactive"]]
    if not active:
        await update.message.reply_text("Không có task active!"); return
    kb = [[InlineKeyboardButton(f"✓ {t['name'][:45]}", callback_data=f"done_{t['id']}")] for t in active]
    await update.message.reply_text("Task nào xong?", reply_markup=InlineKeyboardMarkup(kb))

async def move_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Cú pháp: `/move [id] focus`", parse_mode="Markdown"); return
    try:
        task_id=int(args[0]); slot=args[1].lower(); assert slot in ["focus","reactive","inbox"]
    except:
        await update.message.reply_text("❌ Ví dụ: `/move 3 focus`", parse_mode="Markdown"); return
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"]==task_id), None)
    if not task:
        await update.message.reply_text(f"❌ Không tìm thấy #{task_id}"); return
    if slot=="focus" and sum(1 for t in tasks if t.get("today")=="focus" and not t.get("done"))>=3:
        await update.message.reply_text("⚠️ Tối đa 3 task Focus/ngày!"); return
    task["today"]=slot; save_tasks(tasks)
    await update.message.reply_text(f"✅ *{task['name']}*\n→ {TODAY_LABELS[slot]}", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text: return
    if update.message.chat.type in ["group","supergroup"]:
        bot_username = context.bot.username
        if f"@{bot_username}" not in text: return
        text = text.replace(f"@{bot_username}","").strip()
        if not text:
            await update.message.reply_text("Nhắn gì đi 😄"); return

    tasks = load_tasks(); url = get_webapp_url()

    if is_done(text):
        active = [t for t in tasks if not t.get("done") and t.get("today") in ["focus","reactive"]]
        if not active:
            await update.message.reply_text("Không có task active!"); return
        kb = [[InlineKeyboardButton(f"✓ {t['name'][:45]}", callback_data=f"done_{t['id']}")] for t in active]
        await update.message.reply_text("Task nào xong rồi?", reply_markup=InlineKeyboardMarkup(kb)); return

    parsed = parse_task(text)
    dup = find_dup(parsed["name"], tasks)
    if dup:
        kb = [[InlineKeyboardButton("✅ Đánh dấu xong", callback_data=f"done_{dup['id']}"),
               InlineKeyboardButton("➕ Tạo mới", callback_data=f"force_new_{parsed['name'][:50]}")]]
        await update.message.reply_text(
            f"⚠️ *Giống task đang có:*\n• #{dup['id']} {dup['name']} _[{TODAY_LABELS.get(dup['today'])}]_\n\nBạn muốn?",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb)); return

    if parsed["today"]=="focus" and sum(1 for t in tasks if t.get("today")=="focus" and not t.get("done"))>=3:
        parsed["today"]="inbox"

    task = {"id":next_id(tasks),"name":parsed["name"],"type":parsed["type"],"source":parsed["source"],
            "deadline":parsed["deadline"],"today":parsed["today"],"done":False,"created_at":datetime.now().isoformat()}
    tasks.insert(0,task); save_tasks(tasks)

    dl = datetime.strptime(task["deadline"],"%Y-%m-%d").strftime("%d/%m/%Y")
    btn_row = [InlineKeyboardButton("🎯",callback_data=f"move_{task['id']}_focus"),
               InlineKeyboardButton("⚡",callback_data=f"move_{task['id']}_reactive"),
               InlineKeyboardButton("📥",callback_data=f"move_{task['id']}_inbox")]
    kb = [btn_row]
    if url: kb.append([InlineKeyboardButton("📋 Xem FocusFlow", web_app=WebAppInfo(url=url))])

    await update.message.reply_text(
        f"✅ *#{task['id']}* {task['name']}\n\n• {TYPE_LABELS[task['type']]} · {SOURCE_LABELS[task['source']]} · {dl}\n• {TODAY_LABELS[task['today']]}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    data = query.data; tasks = load_tasks()

    if data.startswith("done_"):
        task = next((t for t in tasks if t["id"]==int(data.split("_")[1])),None)
        if task:
            task["done"]=True; save_tasks(tasks)
            await query.edit_message_text(f"✅ Xong! *{task['name']}* 🎉", parse_mode="Markdown")

    elif data.startswith("force_new_"):
        name = data.replace("force_new_",""); parsed = parse_task(name)
        task = {"id":next_id(tasks),"name":name,"type":parsed["type"],"source":parsed["source"],
                "deadline":parsed["deadline"],"today":parsed["today"],"done":False,"created_at":datetime.now().isoformat()}
        tasks.insert(0,task); save_tasks(tasks)
        await query.edit_message_text(f"✅ *Tạo mới #{task['id']}*\n📌 {task['name']}", parse_mode="Markdown")

    elif data.startswith("move_"):
        parts = data.split("_"); task_id=int(parts[1]); slot=parts[2]
        task = next((t for t in tasks if t["id"]==task_id),None)
        if task:
            if slot=="focus" and sum(1 for t in tasks if t.get("today")=="focus" and not t.get("done") and t["id"]!=task_id)>=3:
                await query.answer("⚠️ Tối đa 3 task Focus/ngày!",show_alert=True); return
            task["today"]=slot; save_tasks(tasks)
            await query.edit_message_text(f"✅ *{task['name']}*\n→ {TODAY_LABELS[slot]}", parse_mode="Markdown")

# ===== MAIN =====
def main():
    threading.Thread(target=run_web_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    for cmd, handler in [("start",start),("app",app_command),("today",today_command),
                          ("inbox",inbox_command),("week",week_command),("done",done_command),("move",move_command)]:
        app.add_handler(CommandHandler(cmd, handler))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("FocusFlow started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__=="__main__":
    main()
