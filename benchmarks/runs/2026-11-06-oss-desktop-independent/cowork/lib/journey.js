'use strict';
const postHeight=()=>parent.postMessage({type:'idli-height',px:Math.ceil(document.documentElement.scrollHeight)},'*');
new ResizeObserver(postHeight).observe(document.body);
const retry=fn=>{$('retry').hidden=false;$('retry').onclick=()=>{$('retry').hidden=true;fn();};};
const reasonText=row=>{
  if(!row.mask)return 'Visible to Claude. You can hide this column if it feels private.';
  const col=row.column.toLowerCase();
  if(/name|beneficiary|employee/.test(col))return 'Names may identify a person.';
  if(/ward|village|town|place|district|address/.test(col))return 'Locations may identify a person or community.';
  if(/phone|mobile|email/.test(col))return 'Contact details are personal.';
  return 'These values may be private. Codes keep the analysis useful.';
};
if(location.pathname==='/privacy-review'){
  let data, busy=false;
  const render=next=>{
    data=next;$('reviews').setAttribute('aria-busy','false');
    $('reviews').innerHTML=data.reviews.map((file,i)=>`<article class="card"><h2 class="file-title">${esc(file.title)}</h2>${file.tabs.map(tab=>`<p class="sheet-title">${esc(tab.tab)}</p>${tab.suggestions.map(row=>`<section class="column-card"><div class="column-head"><label><input class="switch" role="switch" type="checkbox" aria-label="Hide ${esc(row.column)} in ${esc(file.title)}" data-file="${i}" data-col="${esc(row.column)}" ${row.mask?'checked':''} ${data.done?'disabled':''}><span class="column-name">${esc(row.column)}</span></label><span class="visibility">${row.mask?'Hidden':'Visible'}</span></div><p class="reason">${esc(reasonText(row))}</p><div class="samples"><div class="sample"><h3>In your file</h3>${row.samples.map(v=>`<p>${esc(v||'(blank)')}</p>`).join('')}</div><div class="sample masked-sample"><h3>Claude sees</h3>${row.as_sent.map(v=>`<p>${esc(v||'(blank)')}</p>`).join('')}</div></div></section>`).join('')}`).join('')}</article>`).join('');
    $('question-card').hidden=false;$('masked').textContent=data.masked_question;
    $('done').disabled=data.done;$('done').textContent=data.done?'Done':'Done';
    $('hint').textContent=data.done?'Privacy checked. Continue in your chat.':'Your choices apply to these files. Nothing has been sent to Claude.';
    $('reviews').querySelectorAll('input').forEach(el=>el.onchange=async()=>{
      if(busy)return;busy=true;const col=el.dataset.col,local=data.files[Number(el.dataset.file)].local,columns={};
      data.reviews[Number(el.dataset.file)].tabs.forEach(tab=>Object.assign(columns,tab.columns));columns[col]=el.checked;
      $('done').disabled=true;$('reviews').querySelectorAll('input').forEach(x=>x.disabled=true);status('Updating what Claude sees...');
      try{render(await api('/api/review-change',{id:ID,file:local,columns}));status('Choice saved.');}
      catch(e){render(data);status(e.message,true);}
      finally{busy=false;$('done').disabled=!!data.done;}
    });
    postHeight();
  };
  const load=async()=>{try{render(await api('/api/review?id='+encodeURIComponent(ID)));status('Your real samples stay on this computer.');}catch(e){status(e.message,true);retry(load);}};
  $('done').onclick=async()=>{
    if(busy||data?.done)return;busy=true;$('done').disabled=true;status('Returning to your chat...');
    try{await api('/api/review-done',{id:ID});data.done=true;render(data);status('Privacy checked. Your chat has the next step.');}
    catch(e){status(e.message,true);$('done').disabled=false;}finally{busy=false;}
  };load();
}
if(location.pathname==='/mini-editor'){
  let draft,questions=[],charts=[];
  const renderQuestions=()=>{
    $('q-count').textContent=questions.length+' of 8';
    $('questions').innerHTML=questions.map((q,i)=>`<article class="card"><div class="question-top"><label for="question-${i}">Question ${i+1}</label><button type="button" class="remove" data-remove-q="${i}" aria-label="Remove question ${i+1}">Remove</button></div><input id="question-${i}" data-question="${i}" value="${esc(q.question)}" required maxlength="1000">${Object.entries(q.params||{}).map(([key,d])=>`<div class="option"><label>${esc(key)}${d.type==='choice'?`<textarea data-choices="${esc(key)}" data-q="${i}" aria-label="Choices for ${esc(key)}">${esc(d.choices.join('\n'))}</textarea><small>One choice per line.</small>`:''}</label><label>Starting value<input data-default="${esc(key)}" data-q="${i}" type="${d.type==='number'?'number':'text'}" ${d.type==='number'?'step="any"':''} value="${esc(d.default)}" required></label></div>`).join('')}</article>`).join('')||'<p class="empty">Keep at least one question to save this Mini.</p>';
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
    document.querySelectorAll('#editor button').forEach(b=>b.disabled=true);status('Checking the questions and saving your Mini...');
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
      $('editor').hidden=!!draft.saved_id;$('saved').hidden=!draft.saved_id;renderQuestions();renderCharts();status('Edit anything you would like to keep.');
    }catch(e){status(e.message,true);retry(load);}
  };
  $('editor').onsubmit=e=>{e.preventDefault();save('new');};$('add').onclick=()=>save('add');
  $('back-claude').onclick=async()=>{try{await api('/api/claude-back',{ws:draft.workspace});status('Claude is ready on the right.');}catch(e){status(e.message,true);}};
  load();
}
