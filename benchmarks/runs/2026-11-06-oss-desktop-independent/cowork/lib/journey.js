'use strict';
const words=k=>{const t=String(k).replace(/_inr$/i,' (Rs)').replace(/_/g,' ').trim();return t.charAt(0).toUpperCase()+t.slice(1);};
// A card that grows with its content reports its content's height; the page's own height never drops below the frame.
const postHeight=()=>{const m=document.querySelector('main');const card=document.documentElement.classList.contains('card-page')&&m;parent.postMessage({type:'idli-height',px:Math.ceil(card?m.getBoundingClientRect().height+8:document.documentElement.scrollHeight)},'*');};
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
