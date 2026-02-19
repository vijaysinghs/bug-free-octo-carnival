let editing = { achievements: null, goals: null, expenses: null, notes: null, confidential: null };

async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(err.error || 'Request failed');
  }
  return res.json();
}

function showMsg(msg) { alert(msg); }

function showTab(id) {
  document.querySelectorAll('.tab').forEach(t => t.hidden = true);
  document.getElementById(id).hidden = false;
}

async function checkAuth() {
  try {
    const profile = await api('/api/profile');
    document.getElementById('authSection').hidden = true;
    document.getElementById('appSection').hidden = false;
    document.getElementById('logoutBtn').hidden = false;
    document.getElementById('profileLine').textContent = `Logged in as ${profile.username} (${profile.email})`;
    refreshAll();
  } catch {
    document.getElementById('authSection').hidden = false;
    document.getElementById('appSection').hidden = true;
    document.getElementById('logoutBtn').hidden = true;
  }
}

async function register() {
  try {
    await api('/api/register', { method: 'POST', body: JSON.stringify({
      username: regUser.value, email: regEmail.value, password: regPass.value,
    })});
    await checkAuth();
  } catch (e) { showMsg(e.message); }
}

async function login() {
  try {
    await api('/api/login', { method: 'POST', body: JSON.stringify({ username: loginUser.value, password: loginPass.value })});
    await checkAuth();
  } catch (e) { showMsg(e.message); }
}

document.getElementById('logoutBtn').onclick = async () => {
  await api('/api/logout', { method: 'POST' });
  checkAuth();
};

async function refreshAll(){ await Promise.all([loadAchievements(),loadGoals(),loadExpenses(),loadNotes(),loadConfidential()]); }

function renderList(listId, rows, onEdit, onDelete) {
  const ul = document.getElementById(listId);
  ul.innerHTML = '';
  rows.forEach(r => {
    const li = document.createElement('li');
    li.textContent = r.label;
    const e = document.createElement('button'); e.textContent = 'Edit'; e.onclick = () => onEdit(r.raw);
    const d = document.createElement('button'); d.textContent = 'Delete'; d.onclick = () => onDelete(r.raw.id);
    li.append(e,d); ul.appendChild(li);
  });
}

async function loadAchievements() {
  const q = achievementSearch.value ? `?q=${encodeURIComponent(achievementSearch.value)}` : '';
  const rows = await api(`/api/achievements${q}`);
  renderList('achievementList', rows.map(x => ({ raw:x, label:`${x.title} (${x.achieved_on || 'n/a'}): ${x.description}` })),
    (x)=>{ editing.achievements=x.id; achievementTitle.value=x.title; achievementDesc.value=x.description; achievementDate.value=x.achieved_on||''; },
    async(id)=>{ await api(`/api/achievements/${id}`,{method:'DELETE'}); loadAchievements(); });
}
async function saveAchievement(){
  const payload={title:achievementTitle.value,description:achievementDesc.value,achieved_on:achievementDate.value||null};
  if(editing.achievements){ await api(`/api/achievements/${editing.achievements}`,{method:'PUT',body:JSON.stringify(payload)}); editing.achievements=null; }
  else{ await api('/api/achievements',{method:'POST',body:JSON.stringify(payload)}); }
  achievementTitle.value='';achievementDesc.value='';achievementDate.value='';loadAchievements();
}

async function loadGoals() {
  const params = new URLSearchParams();
  if (goalSearch.value) params.set('q', goalSearch.value);
  if (goalFilterStatus.value) params.set('status', goalFilterStatus.value);
  const q = params.toString() ? `?${params.toString()}` : '';
  const rows = await api(`/api/goals${q}`);
  renderList('goalList', rows.map(x => ({ raw:x, label:`${x.title} [${x.status}] target ${x.target_date || 'n/a'}: ${x.description}` })),
    (x)=>{ editing.goals=x.id; goalTitle.value=x.title; goalDesc.value=x.description; goalDate.value=x.target_date||''; goalStatus.value=x.status; },
    async(id)=>{ await api(`/api/goals/${id}`,{method:'DELETE'}); loadGoals(); });
}
async function saveGoal(){
  const payload={title:goalTitle.value,description:goalDesc.value,status:goalStatus.value,target_date:goalDate.value||null};
  if(editing.goals){ await api(`/api/goals/${editing.goals}`,{method:'PUT',body:JSON.stringify(payload)}); editing.goals=null; }
  else{ await api('/api/goals',{method:'POST',body:JSON.stringify(payload)}); }
  goalTitle.value='';goalDesc.value='';goalDate.value='';goalStatus.value='planned';loadGoals();
}

async function loadExpenses() {
  const params = new URLSearchParams();
  if (expenseCategoryFilter.value) params.set('category', expenseCategoryFilter.value);
  if (expenseMin.value) params.set('min_amount', expenseMin.value);
  if (expenseMax.value) params.set('max_amount', expenseMax.value);
  const q = params.toString() ? `?${params.toString()}` : '';
  const rows = await api(`/api/expenses${q}`);
  renderList('expenseList', rows.map(x => ({ raw:x, label:`$${x.amount.toFixed(2)} on ${x.date} [${x.category}] ${x.notes || ''}` })),
    (x)=>{ editing.expenses=x.id; expenseAmount.value=x.amount; expenseDate.value=x.date; expenseCategory.value=x.category; expenseNotes.value=x.notes||''; },
    async(id)=>{ await api(`/api/expenses/${id}`,{method:'DELETE'}); loadExpenses(); });
}
async function saveExpense(){
  const payload={amount:expenseAmount.value,date:expenseDate.value||null,category:expenseCategory.value,notes:expenseNotes.value};
  if(editing.expenses){ await api(`/api/expenses/${editing.expenses}`,{method:'PUT',body:JSON.stringify(payload)}); editing.expenses=null; }
  else{ await api('/api/expenses',{method:'POST',body:JSON.stringify(payload)}); }
  expenseAmount.value='';expenseDate.value='';expenseCategory.value='';expenseNotes.value='';loadExpenses();
}

async function loadNotes() {
  const q = noteSearch.value ? `?q=${encodeURIComponent(noteSearch.value)}` : '';
  const rows = await api(`/api/notes${q}`);
  renderList('noteList', rows.map(x => ({ raw:x, label:`${x.title}: ${x.content}` })),
    (x)=>{ editing.notes=x.id; noteTitle.value=x.title; noteContent.value=x.content; },
    async(id)=>{ await api(`/api/notes/${id}`,{method:'DELETE'}); loadNotes(); });
}
async function saveNote(){
  const payload={title:noteTitle.value,content:noteContent.value};
  if(editing.notes){ await api(`/api/notes/${editing.notes}`,{method:'PUT',body:JSON.stringify(payload)}); editing.notes=null; }
  else{ await api('/api/notes',{method:'POST',body:JSON.stringify(payload)}); }
  noteTitle.value='';noteContent.value='';loadNotes();
}

async function loadConfidential() {
  const q = confSearch.value ? `?q=${encodeURIComponent(confSearch.value)}` : '';
  const rows = await api(`/api/confidential-details${q}`);
  renderList('confList', rows.map(x => ({ raw:x, label:`${x.title}: ${x.value}` })),
    (x)=>{ editing.confidential=x.id; confTitle.value=x.title; confValue.value=x.value; },
    async(id)=>{ await api(`/api/confidential-details/${id}`,{method:'DELETE'}); loadConfidential(); });
}
async function saveConfidential(){
  const payload={title:confTitle.value,value:confValue.value};
  if(editing.confidential){ await api(`/api/confidential-details/${editing.confidential}`,{method:'PUT',body:JSON.stringify(payload)}); editing.confidential=null; }
  else{ await api('/api/confidential-details',{method:'POST',body:JSON.stringify(payload)}); }
  confTitle.value='';confValue.value='';loadConfidential();
}

checkAuth();
