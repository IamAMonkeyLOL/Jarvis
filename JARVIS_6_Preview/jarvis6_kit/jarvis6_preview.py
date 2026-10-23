import json
import os
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path

import streamlit as st
import jarvis_creative

st.set_page_config(page_title='JARVIS 6.0 | Evolution Lab', page_icon='🤖', layout='wide')
ROOT = Path(__file__).resolve().parent
st.markdown('''<style>
.stApp{background:radial-gradient(ellipse at 75% 0%,#102e48 0%,#080e19 48%,#060911 100%);color:#dceefa}
h1,h2,h3{color:#e2f7ff!important}.block-container{padding-top:2rem}
[data-testid="stMetric"]{background:#101e30;border:1px solid #23516a;border-radius:12px;padding:15px}
.stButton button{border:1px solid #1e88aa;background:#102c40;color:#e1f9ff;border-radius:9px}
.hero{border:1px solid #28617e;background:linear-gradient(110deg,#0b1b2c,#112f43);padding:28px;border-radius:18px;margin-bottom:22px}
.glow{color:#5de4ff;letter-spacing:.2em;font-size:12px;font-weight:700}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><div class="glow">● OPERATION EVOLUTION · DEVELOPER PREVIEW</div><h1>JARVIS 6.0</h1><p>Your local AI command centre. Independent of the main Jarvis installation.</p></div>', unsafe_allow_html=True)


def ollama_get(endpoint):
    with urllib.request.urlopen('http://127.0.0.1:11434' + endpoint, timeout=3) as r:
        return json.load(r)

try:
    models = [m.get('name','') for m in ollama_get('/api/tags').get('models',[])]
    online = True
except Exception:
    models, online = [], False

try:
    import psutil
    cpu = f'{psutil.cpu_percent(interval=0.1):.0f}%'
    ram = f'{psutil.virtual_memory().percent:.0f}%'
except ImportError:
    cpu = ram = 'Install psutil'

c1,c2,c3,c4 = st.columns(4)
c1.metric('OLLAMA', 'ONLINE' if online else 'OFFLINE')
c2.metric('CPU',cpu)
c3.metric('MEMORY',ram)
c4.metric('MODELS',len(models))
chat_tab, creative_tab, memory_tab, lab_tab, info_tab = st.tabs(['💬 AI Chat','Blender & D5','🧠 Memory Explorer','🧪 Evolution Lab','🛡️ Safety & Setup'])
with creative_tab:
    jarvis_creative.render()
with chat_tab:
    st.subheader('Talk to Jarvis')
    if not online:
        st.warning('Ollama is offline. Start Ollama to use local chat.')
    selected = st.selectbox('Local model',models if models else ['No models detected'])
    if 'messages' not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])
            st.caption(msg['time'])
    question = st.chat_input('Ask Jarvis anything…',max_chars=50000,disabled=not bool(models))
    if question:
        now=datetime.now().strftime('%H:%M:%S')
        st.session_state.messages.append({'role':'user','content':question,'time':now})
        with st.chat_message('user'): st.write(question)
        with st.chat_message('assistant'):
            try:
                data=json.dumps({'model':selected,'messages':[{'role':m['role'],'content':m['content']} for m in st.session_state.messages], 'stream':False}).encode()
                req=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=data,headers={'Content-Type':'application/json'})
                with st.spinner('Jarvis is thinking…'):
                    with urllib.request.urlopen(req,timeout=180) as r: reply=json.load(r)['message']['content']
            except Exception as e: reply=f'Connection error: {e}'
            st.markdown(reply)
        st.session_state.messages.append({'role':'assistant','content':reply,'time':datetime.now().strftime('%H:%M:%S')})
    left,right=st.columns(2)
    if left.button('Clear this chat'):
        st.session_state.messages=[]
        st.rerun()
    right.download_button('Download this chat',json.dumps(st.session_state.messages,indent=2),file_name='jarvis6_chat.json',mime='application/json')
with memory_tab:
    st.subheader('Local memory database explorer')
    st.info('Read-only preview. It lists SQLite database tables and row counts; it does not display private memory contents or delete data.')
    data_dirs=[ROOT/'data',ROOT.parent/'data']
    dbs=[]
    for folder in data_dirs:
        if folder.is_dir(): dbs.extend(folder.glob('*.db'))
    for db in sorted(set(dbs)):
        with st.expander(db.name):
            try:
                con=sqlite3.connect(f'file:{db.as_posix()}?mode=ro',uri=True)
                tables=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                for table in tables:
                    quoted='"'+table.replace('"','""')+'"'
                    try: st.write(f'{table}: {con.execute("SELECT COUNT(*) FROM "+quoted).fetchone()[0]} records')
                    except sqlite3.Error: st.write(f'{table}: count unavailable')
                con.close()
            except Exception as e: st.error(str(e))
    if not dbs: st.caption('No .db files found in a nearby data/ folder. Existing Jarvis databases are not automatically connected.')
with lab_tab:
    st.subheader('Self-improvement proposal review')
    st.caption('Read-only. Proposals are never executed or applied by this dashboard.')
    proposals=ROOT/'.jarvis_proposals'
    folders=sorted([p for p in proposals.iterdir() if p.is_dir()],reverse=True) if proposals.is_dir() else []
    if not folders: st.info('No proposals found. Copy reviewed proposal folders into .jarvis_proposals/ to inspect their diffs.')
    for folder in folders[:30]:
        with st.expander(folder.name):
            diff=folder/'changes.diff'
            if diff.is_file() and diff.stat().st_size < 500_000: st.code(diff.read_text(encoding='utf-8',errors='replace'),language='diff')
            else: st.caption('No readable diff found.')
with info_tab:
    st.subheader('Preview limitations')
    st.markdown('''- This is a **separate Streamlit application**, not a replacement for your existing Jarvis.
- It does **not** automatically import your existing voice, login, memory or tool integrations.
- Memory explorer is read-only; Evolution Lab only displays diffs.
- Running Ollama models locally does not grant the model permission to modify files.
- The 50,000-character chat input does not increase your model context window.
- For now, launch without administrator permissions.''')
    st.code(str(ROOT))
