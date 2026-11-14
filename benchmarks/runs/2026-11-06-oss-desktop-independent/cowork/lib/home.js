'use strict';
const $ = id => document.getElementById(id);
const TOKEN = new URLSearchParams(location.search).get('t') || '';
const ID = new URLSearchParams(location.search).get('id') || '';
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const link = path => path + (path.includes('?') ? '&' : '?') + 't=' + encodeURIComponent(TOKEN);
async function api(path, body) {
  const r = await fetch(link(path), body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await r.json();
  if (!r.ok || data.error) throw Error(data.error || 'Could not complete the request');
  return data;
}
function status(text, error=false) { $('status').textContent=text; $('status').className=error?'error':''; }
if ($('homelink')) $('homelink').href=link('/home');

if (location.pathname === '/home') {
  let files=[], prepared=null, picks=[], highlight=0, target=null, serial=0, revision=0;
  const key = f => f.local || f.id;
  function hidePicker() {
    serial++; picks=[];
    for (const [input, box] of [[$('search'),$('hits')],[$('question'),$('mentions')]]) {
      box.hidden=true; input.setAttribute('aria-expanded','false'); input.removeAttribute('aria-activedescendant');
    }
  }
  function invalidate() { revision++; prepared=null; $('review').hidden=true; $('compose').hidden=false; }
  function chips() {
    $('chips').innerHTML=files.map((f,i)=>`<span class="chip">${esc(f.title)}<button data-i="${i}" aria-label="Remove ${esc(f.title)}">×</button></span>`).join('');
    $('chips').querySelectorAll('button').forEach(b=>b.onclick=()=>{files.splice(Number(b.dataset.i),1);invalidate();chips();});
  }
  function add(f) {
    if (!files.some(x=>key(x)===key(f))) files.push(f);
    if (target === $('question')) {
      const el=$('question'), pos=el.selectionStart, start=el.value.lastIndexOf('@',pos-1);
      if (start>=0) {el.value=el.value.slice(0,start)+el.value.slice(pos);el.setSelectionRange(start,start);}
    } else $('search').value='';
    invalidate(); chips(); hidePicker(); $('question').focus();
  }
  async function picker(input, query) {
    const version=++serial; target=input;
    const box=input===$('search')?$('hits'):$('mentions');
    try {
      const data=await api('/api/home/search?q='+encodeURIComponent(query));
      if(version!==serial)return;
      picks=data.results.filter(f=>!files.some(x=>key(x)===key(f)));highlight=0;
      for (const id of ['hits','mentions']) $(id).hidden=true;
      box.innerHTML=picks.length?picks.map((f,i)=>`<button type="button" id="pick-${i}" role="option" aria-selected="${i===0}" class="${i===0?'on':''}" data-i="${i}">${esc(f.title)}<small>${esc(f.folder)}</small></button>`).join(''):'<p class="muted">No matching files.</p>';
      box.hidden=false;input.setAttribute('aria-expanded','true');input.setAttribute('aria-activedescendant','pick-0');
      box.querySelectorAll('button').forEach(b=>b.onmousedown=e=>{e.preventDefault();add(picks[Number(b.dataset.i)]);});
    } catch(e) {if(version===serial)status(e.message,true);}
  }
  $('search').oninput=()=>picker($('search'),$('search').value);
  $('search').onfocus=()=>picker($('search'),$('search').value);
  $('question').oninput=()=>{
    invalidate(); const el=$('question'), before=el.value.slice(0,el.selectionStart), at=before.lastIndexOf('@');
    if(at>=0 && (at===0 || /\s/.test(before[at-1])) && !before.slice(at).includes('\n')) picker(el,before.slice(at+1)); else hidePicker();
  };
  for(const el of [$('search'),$('question')]) el.addEventListener('keydown',e=>{
    if(e.key==='Escape'){hidePicker();return;}
    if(el!==target || !picks.length)return;
    if(e.key==='Enter'||e.key==='Tab'){e.preventDefault();add(picks[highlight]);}
    if(e.key==='ArrowDown'||e.key==='ArrowUp'){
      e.preventDefault();highlight=(highlight+(e.key==='ArrowDown'?1:-1)+picks.length)%picks.length;
      const box=el===$('search')?$('hits'):$('mentions');
      box.querySelectorAll('button').forEach((b,i)=>{b.classList.toggle('on',i===highlight);b.setAttribute('aria-selected',String(i===highlight));});
      el.setAttribute('aria-activedescendant','pick-'+highlight);box.querySelector('.on').scrollIntoView({block:'nearest'});
    }
  });
  document.addEventListener('mousedown',e=>{if(!e.target.closest('.picker'))hidePicker();});
  function renderReview(data) {
    prepared=data;files=data.files;chips();$('masked').textContent=data.masked_question;
    $('reviews').innerHTML=data.reviews.map((f,i)=>`<article class="card"><h3>${esc(f.title)}</h3>${f.tabs[0]?.mode!=='mask'?`<p>This file uses Fake copy. <button data-mask="${i}">Use Mask for Claude</button></p>`:''}${f.tabs.map(tab=>`<p>${esc(tab.tab)}</p><div class="scroll"><table><thead><tr><th>Mask column</th><th>Why</th><th>Real samples</th><th>As sent</th></tr></thead><tbody>${tab.suggestions.map(r=>`<tr><td><label><input type="checkbox" data-file="${i}" data-col="${esc(r.column)}" ${r.mask?'checked':''}>${esc(r.column)}</label></td><td>${esc(r.reason)}</td><td>${esc(r.samples.join(' · '))}</td><td>${esc(r.as_sent.join(' · '))}</td></tr>`).join('')}</tbody></table></div>`).join('')}</article>`).join('');
    $('reviews').querySelectorAll('input').forEach(el=>el.onchange=async()=>{
      $('send').disabled=true;$('back').disabled=true;$('reviews').querySelectorAll('input').forEach(x=>x.disabled=true);
      try {
        const f=data.reviews[Number(el.dataset.file)], columns={};
        f.tabs.forEach(t=>Object.assign(columns,t.columns)); columns[el.dataset.col]=el.checked;
        await api('/api/privacy',{file:f.local,mode:'mask',columns});
        renderReview(await api('/api/home/prepare',{files,question:$('question').value}));status('Privacy updated.');
      } catch(e){el.checked=!el.checked;status(e.message,true);}
      finally{$('send').disabled=false;$('back').disabled=false;$('reviews').querySelectorAll('input').forEach(x=>x.disabled=false);}
    });
    $('reviews').querySelectorAll('[data-mask]').forEach(button=>button.onclick=async()=>{
      $('send').disabled=true;$('back').disabled=true;button.disabled=true;
      try {
        await api('/api/privacy',{file:data.reviews[Number(button.dataset.mask)].local,mode:'mask'});
        renderReview(await api('/api/home/prepare',{files,question:$('question').value}));status('Mask selected.');
      }catch(e){status(e.message,true);button.disabled=false;}
      finally{$('send').disabled=false;$('back').disabled=false;}
    });
    $('compose').hidden=true;$('review').hidden=false;
  }
  $('next').onclick=async()=>{
    if(!files.length || !$('question').value.trim()){status('Choose a file and write a question.',true);return;}
    const v=revision;hidePicker();$('next').disabled=true;status('Preparing your files…');
    try {const data=await api('/api/home/prepare',{files,question:$('question').value});if(v===revision){renderReview(data);status('Check the columns and question before sending.');}}
    catch(e){status(e.message,true);}finally{$('next').disabled=false;}
  };
  $('back').onclick=()=>{invalidate();status('');};
  $('send').onclick=async()=>{
    if(!prepared)return;$('send').disabled=true;$('back').disabled=true;status('Opening Claude…');
    try {const data=await api('/api/home/send',{files:prepared.files,question:$('question').value});files=[];$('question').value='';$('search').value='';invalidate();chips();status(data.message+(data.focused?'':'. Click its tab if it is not visible.'));}
    catch(e){status(e.message,true);}finally{$('send').disabled=false;$('back').disabled=false;}
  };
  api('/api/home/minis').then(rows=>{$('minis').innerHTML=rows.length?rows.map(m=>`<a class="card" href="${esc(link('/mini?id='+encodeURIComponent(m.id)))}"><h3>${esc(m.name)}</h3><p>${esc(m.goal)}</p><small>${m.questions} questions</small></a>`).join(''):'<p class="muted">Minis you make with Claude will appear here.</p>';}).catch(e=>status(e.message,true));
}

// Claude's charts (idli_show) open here in Idli's pane: the home page watches for a new one and goes to it.
if (location.pathname === '/home') {
  let seen;
  const watch = async () => {
    try {
      const r = await fetch(link('/api/home/latest-view'));
      const view = (await r.json()).view;
      if (seen === undefined) seen = view;
      else if (view && view !== seen) { location.href = link('/view?id=' + encodeURIComponent(view)); return; }
    } catch (e) { /* the server restarts now and then */ }
    setTimeout(watch, 2000);
  };
  watch();
}

// Opened by Paseo for a Drivey workspace (/home-open?ws=…): make sure that workspace's Claude CLI is on the right.
if (location.pathname === '/home') {
  const ws = new URLSearchParams(location.search).get('ws') || '';
  if (ws) fetch(link('/api/home/claude'), {method: 'POST', headers: {'Content-Type': 'application/json'},
                                           body: JSON.stringify({workspace: ws})}).catch(() => {});
}
