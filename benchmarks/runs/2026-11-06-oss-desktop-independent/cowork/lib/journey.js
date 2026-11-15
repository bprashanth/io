'use strict';
const words=k=>{const t=String(k).replace(/_inr$/i,' (Rs)').replace(/_/g,' ').trim();return t.charAt(0).toUpperCase()+t.slice(1);};
const postHeight=()=>parent.postMessage({type:'idli-height',px:Math.ceil(document.documentElement.scrollHeight)},'*');
new ResizeObserver(postHeight).observe(document.body);
const retry=fn=>{$('retry').hidden=false;$('retry').onclick=()=>{$('retry').hidden=true;fn();};};
const reasonText=row=>{
  if(!row.mask)return 'Visible to Claude.';
  const col=row.column.toLowerCase();
  if(/name|beneficiary|employee|head|owner|respondent|farmer|guardian|father|mother|spouse/.test(col))return 'Names.';
  if(/(^|_)(lat|lon|lng|latitude|longitude|gps)($|_)/.test(col))return 'Exact location.';
  if(/ward|village|town|place|district|address/.test(col))return 'Place.';
  if(/phone|mobile|email/.test(col))return 'Contact details.';
  return 'May be private.';
};
if(location.pathname==='/privacy-review'){
  let data, busy=false;
  const render=next=>{
    data=next;$('reviews').setAttribute('aria-busy','false');
    const row=(row,i)=>`<div class="col-row${row.mask?' hidden-col':''}"><input class="switch" role="switch" type="checkbox" aria-label="Hide ${esc(words(row.column))} in ${esc(data.reviews[i].title)}" data-file="${i}" data-col="${esc(row.column)}" ${row.mask?'checked':''} ${data.done?'disabled':''}><div class="col-text"><div class="column-name">${esc(words(row.column))}</div><div class="col-sample">${esc(row.samples[0]||'(blank)')}${row.mask?` <span class="dim">-></span> <code>${esc(row.as_sent[0]||'')}</code>`:''}</div>${row.mask?`<div class="reason">${esc(reasonText(row))}</div>`:''}</div></div>`;
    $('reviews').innerHTML=data.reviews.map((file,i)=>{
      const tabs=file.tabs.map(tab=>{
        const hid=tab.suggestions.filter(r=>r.mask),vis=tab.suggestions.filter(r=>!r.mask);
        const many=file.tabs.length>1?`<p class="sheet-title">${esc(tab.tab)}</p>`:'';
        return many+`<p class="group-title">Hidden with codes (${hid.length})</p>`+(hid.map(r=>row(r,i)).join('')||'<p class="empty">Nothing hidden in this sheet.</p>')+
          `<details class="visible-group"${hid.length?'':' open'}><summary>Claude can see ${vis.length} column${vis.length===1?'':'s'}: <span class="dim">${esc(vis.map(r=>words(r.column).toLowerCase()).join(', '))}</span></summary>${vis.map(r=>row(r,i)).join('')}</details>`;
      }).join('');
      return `<article class="card"><h2 class="file-title">${esc(file.title)}</h2>${tabs}</article>`;
    }).join('');
    $('question-card').hidden=false;$('masked').textContent=data.masked_question;
    $('done').disabled=data.done;$('done').textContent=data.done?'Done':'Done';
    $('hint').textContent=data.done?'Privacy checked. Continue in your chat.':'Nothing is sent yet.';
    $('reviews').querySelectorAll('input').forEach(el=>el.onchange=async()=>{
      if(busy)return;busy=true;const col=el.dataset.col,local=data.files[Number(el.dataset.file)].local,columns={};
      data.reviews[Number(el.dataset.file)].tabs.forEach(tab=>Object.assign(columns,tab.columns));columns[col]=el.checked;
      $('done').disabled=true;$('reviews').querySelectorAll('input').forEach(x=>x.disabled=true);status('Updating...');
      try{render(await api('/api/review-change',{id:ID,file:local,columns}));status('Saved.');}
      catch(e){render(data);status(e.message,true);}
      finally{busy=false;$('done').disabled=!!data.done;}
    });
    postHeight();
  };
  const load=async()=>{try{render(await api('/api/review?id='+encodeURIComponent(ID)));status('Real values stay on this computer.');}catch(e){status(e.message,true);retry(load);}};
  $('done').onclick=async()=>{
    if(busy||data?.done)return;busy=true;$('done').disabled=true;status('Returning to your chat...');
    try{await api('/api/review-done',{id:ID});data.done=true;render(data);status('Privacy checked.');}
    catch(e){status(e.message,true);$('done').disabled=false;}finally{busy=false;}
  };load();
}
if(location.pathname==='/mini-editor'||location.pathname==='/mini-card'){
  if(new URLSearchParams(location.search).get('embed')==='1')document.documentElement.classList.add('embed');
  let draft,questions=[],charts=[];
  const renderQuestions=()=>{
    $('q-count').textContent=questions.length+' of 8';
    $('questions').innerHTML=questions.map((q,i)=>`<article class="card"><div class="question-top"><label for="question-${i}">Question ${i+1}</label><button type="button" class="remove" data-remove-q="${i}" aria-label="Remove question ${i+1}">Remove</button></div><input id="question-${i}" data-question="${i}" value="${esc(q.question)}" required maxlength="1000">${Object.entries(q.params||{}).map(([key,d])=>`<div class="option"><div class="option-name">${esc(words(key))}</div>${d.type==='choice'?`<label>Choices <small>one per line</small><textarea data-choices="${esc(key)}" data-q="${i}" rows="${Math.min(6,d.choices.length)}" aria-label="Choices for ${esc(words(key))}">${esc(d.choices.join('\n'))}</textarea></label>`:''}<label>${d.type==='choice'?'Starts with':'Starts at'}<input data-default="${esc(key)}" data-q="${i}" type="${d.type==='number'?'number':'text'}" ${d.type==='number'?'step="any"':''} value="${esc(d.default)}" required></label></div>`).join('')}</article>`).join('')||'<p class="empty">Keep at least one question to save this Mini.</p>';
    $('questions').querySelectorAll('[data-question]').forEach(el=>el.oninput=()=>{questions[Number(el.dataset.question)].question=el.value;});
    $('questions').querySelectorAll('[data-default]').forEach(el=>el.oninput=()=>{const d=questions[Number(el.dataset.q)].params[el.dataset.default];d.default=d.type==='number'?Number(el.value):el.value;});
    $('questions').querySelectorAll('[data-choices]').forEach(el=>el.oninput=()=>{questions[Number(el.dataset.q)].params[el.dataset.choices].choices=el.value.split('\n').map(v=>v.trim()).filter(Boolean);});
    $('questions').querySelectorAll('[data-remove-q]').forEach(b=>b.onclick=()=>{questions.splice(Number(b.dataset.removeQ),1);renderQuestions();status('Question removed from this draft.');});
    postHeight();
  };
  const renderCharts=()=>{
    $('chart-count').textContent=charts.length;
    $('charts').innerHTML=charts.map((c,i)=>`<div class="card pinned-chart"><a href="${esc(link('/view?id='+encodeURIComponent(c.id)))}" target="_blank" rel="noopener">${esc(c.title)}</a><button type="button" class="remove" data-remove-chart="${i}" aria-label="Remove chart ${esc(c.title)}">Remove</button></div>`).join('')||'<p class="empty">No charts kept yet. You can go back to a chart and pin it before making another draft.</p>';
    $('charts').querySelectorAll('button').forEach(b=>b.onclick=()=>{charts.splice(Number(b.dataset.removeChart),1);renderCharts();status('Chart removed from this draft.');});postHeight();
  };
  const save=async action=>{
    if(!$('editor').reportValidity())return;
    if(!questions.length){status('Keep at least one question before saving.',true);return;}
    document.querySelectorAll('#editor button').forEach(b=>b.disabled=true);status('Checking and saving...');
    try{
      await api('/api/mini-save',{id:ID,action,name:$('name').value,goal:$('story').value,questions,charts:charts.map(c=>c.id)});
      $('editor').hidden=true;$('saved').hidden=false;status('Saved.');$('saved').setAttribute('tabindex','-1');$('saved').focus();
    }catch(e){status(e.message,true);}finally{document.querySelectorAll('#editor button').forEach(b=>b.disabled=false);}
  };
  const load=async()=>{
    try{
      draft=await api('/api/mini-draft?id='+encodeURIComponent(ID));questions=structuredClone(draft.questions);charts=structuredClone(draft.charts||[]);
      $('name').value=draft.name;$('story').value=draft.goal;$('code').textContent=draft.code||'Saved with this Mini';
      $('sources').textContent=(draft.files||[]).map(f=>f.local).join('\n')||'No files recorded';
      if(draft.source_id){$('add').hidden=false;$('add').textContent='Add to '+draft.source_name;$('save').textContent='Save as a new Mini';}
      $('editor').hidden=!!draft.saved_id;$('saved').hidden=!draft.saved_id;renderQuestions();renderCharts();status('');
    }catch(e){status(e.message,true);retry(load);}
  };
  $('editor').onsubmit=e=>{e.preventDefault();save('new');};$('add').onclick=()=>save('add');
  $('back-claude').onclick=async()=>{try{await api('/api/claude-back',{ws:draft.workspace});status('Claude is ready on the right.');}catch(e){status(e.message,true);}};
  load();
}
