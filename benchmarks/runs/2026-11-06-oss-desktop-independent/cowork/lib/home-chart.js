'use strict';
let AGENT='', chartTitle='', chartMeta={}, chartRows=[];
const QUERY_WS=new URLSearchParams(location.search).get('ws')||'';
let WS=QUERY_WS;
const EMBED=location.pathname==='/view'&&new URLSearchParams(location.search).get('embed')==='1';
function cleanSpec(spec) {
  // Every chart's data is supplied locally, including nested specs and named datasets.
  // Vega's interpreter also avoids eval under the server's CSP.
  const clean=node=>{
    if(Array.isArray(node))return node.map(clean);
    if(node && typeof node==='object')return Object.fromEntries(Object.entries(node).filter(([k])=>!['url','href','datasets'].includes(k)).map(([k,v])=>[k,clean(v)]));
    return node;
  };
  return clean(spec);
}
let chartView=null, bigger=false;
async function draw(spec, data, agent, title, meta={}) {
  AGENT=agent||'';chartTitle=title||'chart';chartMeta=meta;chartRows=data;WS=QUERY_WS||meta.workspace||'';unpop();
  if(chartView){chartView.finalize();chartView=null;}
  const local=cleanSpec(spec);
  local.data={values:data};
  const composite=local.facet||local.concat||local.hconcat||local.vconcat||local.repeat;
  if(!composite)local.width=EMBED?Math.max(140,innerWidth-16):Math.max(140,Math.min(760,$('viz').clientWidth-64))*(bigger?1.6:1);
  if(!EMBED&&!composite){local.height=bigger?420:260;local.autosize={type:'fit',contains:'padding',resize:true};}
  if(EMBED&&!composite){local.height=Math.max(100,innerHeight-16);local.autosize={type:'fit',contains:'padding',resize:true};}
  const style=getComputedStyle(document.body),ink=style.color,line=style.getPropertyValue('--line').trim(),accent=style.getPropertyValue('--accent').trim();
  local.background='transparent';
  local.config={...local.config,background:'transparent',range:{category:[accent,'#719c8d','#b5a379','#8b8fa8','#b37f72']},axis:{...local.config?.axis,labelColor:ink,titleColor:ink,gridColor:line,domainColor:line,tickColor:line},legend:{...local.config?.legend,labelColor:ink,titleColor:ink},title:{...local.config?.title,color:ink},text:{...local.config?.text,color:ink}};
  const result=await vegaEmbed('#viz',local,{actions:false,renderer:'svg',ast:true,expr:vega.expressionInterpreter});
  chartView=result.view;
  if(EMBED||composite){
    // Facets and concatenated charts do not support Vega-Lite's fit autosize.
    const svg=$('viz').querySelector('svg'),w=Number(svg.getAttribute('width')),h=Number(svg.getAttribute('height'));
    const scale=EMBED?Math.min(1,(innerWidth-16)/w,(innerHeight-16)/h):Math.min(1,Math.max(140,$('viz').clientWidth-16)/w)*(bigger?1.6:1);
    svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.setAttribute('width',w*scale);svg.setAttribute('height',h*scale);
  }
  chartView.addEventListener('click',(ev,item)=>pop(ev,item&&item.datum));
  chartView.addEventListener('contextmenu',(ev,item)=>{if(item&&item.datum){ev.preventDefault();contextMenu(ev,item.datum);}});
}
function fields(datum) {
  return Object.keys(datum||{}).filter(k=>!/(^__|_start$|_end$|sort_index)/.test(k)&&datum[k]!==undefined&&typeof datum[k]!=='object');
}
function showPop(ev, role='dialog') {
  const el=$('pop');el.setAttribute('role',role);el.hidden=false;document.body.classList.add('popping');
  el.style.left=Math.max(16,Math.min((ev?.clientX||40)+8,innerWidth-el.offsetWidth-16))+'px';
  el.style.top=Math.max(16,Math.min((ev?.clientY||120)+8,innerHeight-el.offsetHeight-16))+'px';
}
// Plain words for people: "total_debt_inr" -> "Total debt (Rs)", 350000 -> "3,50,000".
function human(k) {
  let t=String(k).replace(/_inr$/i,' (Rs)').replace(/_?1to10$/i,' (1 to 10)').replace(/_/g,' ').trim();
  return t.charAt(0).toUpperCase()+t.slice(1);
}
function nice(v) {
  if(typeof v==='number'||(String(v).trim()!==''&&!isNaN(Number(v))&&/^-?[\d.]+$/.test(String(v).trim()))){
    const n=Number(v);return Number.isInteger(n)?n.toLocaleString('en-IN'):n.toLocaleString('en-IN',{maximumFractionDigits:2});
  }
  return String(v??'');
}
function fileParts(path) {
  const parts=String(path||'').replace(/^drive\//,'').split('/'),file=parts.pop()||'';
  return {name:file.replace(/\.(xlsx|xls|csv)$/i,''),folder:parts.join(' / ')};
}
function scriptName(path) {
  return String(path||'').split('/').pop().replace(/\.py$/,'').replace(/[_-]+/g,' ');
}
function provenance(datum) {
  const el=$('pop'),keys=fields(datum).filter(k=>chartRows.some(r=>Object.hasOwn(r,k)));
  // Match the mark's CSV fields. Vega may add aggregate fields that are absent from the CSV.
  const equal=(a,b)=>String(a)===String(b)||(typeof b==='number'&&String(a).trim()!==''&&Number(a)===b);
  const rows=keys.length?chartRows.filter(r=>keys.every(k=>equal(r[k],datum[k]))):[];
  const columns=[...new Set(rows.flatMap(r=>Object.keys(r)))];
  const files=(chartMeta.sources||[]).map(fileParts);
  const from=files.length?files.map(f=>`<b>${esc(f.name)}</b>`+(f.folder?` <span class="dim">(${esc(f.folder)})</span>`:'')).join(', '):'a file Idli did not record';
  const made=chartMeta.script?`Script: <b>${esc(scriptName(chartMeta.script))}</b>`:'';
  let detail;
  if(rows.length===1){
    detail=`<p class="lead">This part of the chart</p><dl>${columns.map(k=>`<dt>${esc(human(k))}</dt><dd>${esc(nice(rows[0][k]))}</dd>`).join('')}</dl>`;
  } else if(rows.length){
    const shown=rows.slice(0,10);
    detail=`<p class="lead">${rows.length} rows make up this part${rows.length>10?' (first 10 shown)':''}</p><div class="scroll"><table><thead><tr>${columns.map(k=>`<th>${esc(human(k))}</th>`).join('')}</tr></thead><tbody>${shown.map(r=>`<tr>${columns.map(k=>`<td>${esc(nice(r[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  } else detail='<p class="dim">No single row: this part is a summary.</p>';
  const paths=[...(chartMeta.sources||[]),chartMeta.script,chartMeta.data_csv].filter(Boolean);
  el.innerHTML=`<div class="what">Where did this come from?</div><p>Source: ${from}. Claude saw ${files.length>1?'them':'it'} with codes.</p>`+
    (made?`<p>${made}</p>`:'')+detail+
    (paths.length?`<details><summary>File details</summary><pre>${esc(paths.join('\n'))}</pre></details>`:'');
}
function contextText(datum) {
  const one=value=>String(value??'').replace(/\s+/g,' ').trim();
  const sources=(chartMeta.sources||[]).map(x=>`redacted(${one(x)})`).join(', ')||'-';
  const script=one(chartMeta.script).split('/').pop()||'-';
  const part=datum?', the part '+fields(datum).map(k=>`${one(k)} = ${one(datum[k])}`).join(', '):'';
  return `About the chart "${one(chartTitle)}"${part} (from: ${sources}; script: ${script}; data: ${one(chartMeta.data_csv)||'-'}) `;
}
function contextMenu(ev,datum) {
  const el=$('pop');
  el.innerHTML='<button role="menuitem" data-copy="element">Copy to Claude</button><button role="menuitem" data-copy="chart">Copy whole chart to Claude</button>';
  el.querySelectorAll('button').forEach(b=>b.onclick=async()=>{
    if(!WS){el.textContent='Open this chart in a Drivey workspace to copy to Claude.';return;}
    try{await api('/api/claude-insert',{ws:WS,text:contextText(b.dataset.copy==='element'?datum:null)});unpop();}
    catch(e){el.textContent=e.message;}
  });
  showPop(ev,'menu');
}
function pop(ev,datum) {
  if(!datum)return;
  const el=$('pop'),keys=fields(datum);
  const nums=keys.filter(k=>typeof datum[k]==='number'),labs=keys.filter(k=>!nums.includes(k));
  const what=labs.map(k=>datum[k]).join(' / ')||'this point';
  const val=nums.map(k=>`${human(k)}: ${nice(datum[k])}`).join(' - ');
  const piece=`the ${what} mark`+(val?` (${val})`:'')+` on "${chartTitle}"`;
  const say=async text=>{
    el.innerHTML='<div class="note">Sending...</div>';
    try{await api(WS?'/api/claude-question':'/api/say',{agent:AGENT,...(WS?{ws:WS}:{}),text:text.slice(0,800)});el.innerHTML='<div class="note">Sent to Claude.</div>';setTimeout(unpop,1200);}
    catch(e){el.textContent=e.message;}
  };
  const disabled=!(WS||AGENT)?' disabled':'';
  el.innerHTML=`<div class="what">${esc(what)}<div class="note">${esc(val)}</div></div><button data-q="source">Where did this come from?</button><button data-q="calc"${disabled}>How is this number worked out?</button><button data-q="rows"${disabled}>Show the rows behind it</button><button data-q="cmp"${disabled}>Compare it with the others</button><button data-q="wrong"${disabled}>This looks wrong</button><textarea aria-label="Comment" placeholder="Or write a comment about it..."></textarea><button data-q="note"${disabled}>Send comment</button>`;
  const questions={calc:`How is ${piece} worked out?`,rows:`Show me the rows behind ${piece}.`,cmp:`Compare ${what} with the others on "${chartTitle}".`,wrong:`${piece} looks wrong to me. Check it.`};
  el.querySelectorAll('button').forEach(b=>b.onclick=()=>{
    if(b.dataset.q==='source')provenance(datum);
    else if(b.dataset.q==='note'){const t=el.querySelector('textarea').value.trim();if(t)say(`About ${piece}: ${t}`);}
    else say(questions[b.dataset.q]);
  });
  showPop(ev);
}
function unpop(){ $('pop').hidden=true;document.body.classList.remove('popping'); }
document.addEventListener('keydown',e=>{if(e.key==='Escape')unpop();});
document.addEventListener('mousedown',e=>{if(!e.target.closest('#pop,#viz'))unpop();});

function answerHTML(text) {
  const lines=String(text).split('\n'),out=[];
  for(let i=0;i<lines.length;i++){
    if(lines[i].trim().startsWith('|') && /^\s*\|?[\s:|-]+\|\s*$/.test(lines[i+1]||'')){
      const cells=l=>l.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());
      let table='<div class="scroll"><table><thead><tr>'+cells(lines[i]).map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>';i+=2;
      while(i<lines.length&&lines[i].trim().startsWith('|')){table+='<tr>'+cells(lines[i]).map(x=>'<td>'+esc(x)+'</td>').join('')+'</tr>';i++;}
      i--;out.push(table+'</tbody></table></div>');
    }else out.push('<div style="white-space:pre-wrap">'+esc(lines[i])+'</div>');
  }
  return out.join('');
}
if(location.pathname==='/view') api('/api/view?id='+encodeURIComponent(ID)).then(async v=>{
  document.title=v.title;$('title').textContent=v.title;await draw(v.spec,v.data,v.agent,v.title,v);status('');
  const pin=$('pin'),zoom=$('zoom');
  const pinLabel=()=>{pin.textContent=v.pinned?'Pinned':'Pin';pin.setAttribute('aria-pressed',String(!!v.pinned));};
  pin.disabled=false;zoom.disabled=false;pinLabel();
  pin.onclick=async()=>{pin.disabled=true;try{const r=await api('/api/view/pin',{id:ID,pinned:!v.pinned});v.pinned=r.pinned;pinLabel();status(v.pinned?'Pinned. It goes in your next Mini.':'Unpinned.');}catch(e){status(e.message,true);}finally{pin.disabled=false;}};
  zoom.onclick=async()=>{bigger=!bigger;zoom.textContent=bigger?'Zoom: Bigger':'Zoom: Fit';zoom.setAttribute('aria-pressed',String(bigger));try{await draw(v.spec,v.data,v.agent,v.title,v);}catch(e){status('The chart could not draw. Choose Zoom to try again.',true);}};
  $('claude-back').onclick=async()=>{try{await api('/api/claude-back',{ws:WS});status('Claude is ready on the right.');}catch(e){status(e.message,true);}};
  if(EMBED)parent.postMessage({type:'idli-height',px:Number(new URLSearchParams(location.search).get('h'))||360},'*');
  let resize;const redraw=()=>{clearTimeout(resize);resize=setTimeout(()=>draw(v.spec,v.data,v.agent,v.title,v).catch(e=>status(e.message,true)),100);};
  window.addEventListener('resize',redraw);matchMedia('(prefers-color-scheme: dark)').addEventListener('change',redraw);
}).catch(e=>{status('This chart could not open. Return to Claude and ask to show it again.',true);});

if(location.pathname==='/mini') (async()=>{
  try{
    const m=await api('/api/mini?id='+encodeURIComponent(ID));document.title=m.name;$('title').textContent=m.name;$('goal').textContent=m.goal;
    $('questions').innerHTML=m.questions.map((q,i)=>`<section class="card" id="q-${i}"><button class="qpick" data-i="${i}">${esc(q.question)}</button><div class="params">${Object.entries(q.params||{}).map(([name,d])=>`<label>${esc(name)}${d.type==='choice'?`<select data-param="${esc(name)}">${d.choices.map(v=>`<option value="${esc(v)}" ${String(v)===String(d.default)?'selected':''}>${esc(v)}</option>`).join('')}</select>`:`<input data-param="${esc(name)}" type="${d.type==='number'?'number':'text'}" ${d.type==='number'?'step="any"':''} value="${esc(d.default)}">`}</label>`).join('')}</div><button class="run primary" data-i="${i}">Run</button></section>`).join('');
    const pick=i=>{document.querySelectorAll('#questions .card').forEach((el,j)=>el.classList.toggle('picked',j===i));};
    document.querySelectorAll('.qpick').forEach(b=>b.onclick=()=>{pick(Number(b.dataset.i));$('q-'+b.dataset.i).querySelector('input,select,.run').focus();});
    document.querySelectorAll('.run').forEach(b=>b.onclick=async()=>{
      const i=Number(b.dataset.i),q=m.questions[i],params={};
      $('q-'+i).querySelectorAll('[data-param]').forEach(el=>{const d=q.params[el.dataset.param];params[el.dataset.param]=d.type==='number'?Number(el.value):d.type==='choice'?d.choices.find(v=>String(v)===el.value):el.value;});
      pick(i);$('mapping').textContent=`${q.question} - ${JSON.stringify(params)}`;status('Running…');
      document.querySelectorAll('.run,#match').forEach(el=>el.disabled=true);
      try{
        const r=await api('/api/mini/run',{id:ID,qid:q.id,params});$('result').hidden=false;$('result-title').textContent=q.question;$('result-params').textContent='Run with '+JSON.stringify(r.params);$('answer').innerHTML=answerHTML(r.text);$('viz').innerHTML='';
        if(r.chart)await draw(r.chart.vega_lite,r.chart.data,r.agent,q.question,r);else unpop();status('Done.');
      }catch(e){status(e.message,true);}finally{document.querySelectorAll('.run,#match').forEach(el=>el.disabled=false);}
    });
    $('match').onclick=async()=>{
      if(!$('ask').value.trim())return;$('match').disabled=true;status('Finding a saved question…');
      try{
        const r=await api('/api/mini/map',{id:ID,question:$('ask').value});const i=m.questions.findIndex(q=>q.id===r.qid);
        if(i<0){$('mapping').textContent="I don't know. This Mini can answer: "+m.questions.map(q=>q.question).join('; ');status('');return;}
        pick(i);
        $('q-'+i).querySelectorAll('[data-param]').forEach(el=>{if(r.params[el.dataset.param]!=null)el.value=r.params[el.dataset.param];});
        $('mapping').textContent=`Picked: ${m.questions[i].question} - ${JSON.stringify(r.params)} (${r.method}). Check the inputs, then Run.`;
        $('q-'+i).scrollIntoView({block:'nearest',behavior:'smooth'});status('');
      }catch(e){status(e.message,true);}finally{$('match').disabled=false;}
    };
  }catch(e){status(e.message,true);}
})();
