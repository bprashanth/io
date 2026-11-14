'use strict';
let AGENT='', chartTitle='';
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
let chartView=null;
async function draw(spec, data, agent, title) {
  AGENT=agent||'';chartTitle=title||'chart';unpop();
  if(chartView){chartView.finalize();chartView=null;}
  const local=cleanSpec(spec);
  local.data={values:data};
  local.width=Math.max(140,Math.min(680,$('viz').clientWidth-70));
  local.config={...local.config,background:'transparent',axis:{labelColor:getComputedStyle(document.body).color,titleColor:getComputedStyle(document.body).color},legend:{labelColor:getComputedStyle(document.body).color,titleColor:getComputedStyle(document.body).color}};
  const result=await vegaEmbed('#viz',local,{actions:false,renderer:'svg',ast:true,expr:vega.expressionInterpreter});
  chartView=result.view;
  chartView.addEventListener('click',(ev,item)=>pop(ev,item&&item.datum));
}
function pop(ev,datum) {
  if(!datum||!AGENT)return;
  const el=$('pop'),keys=Object.keys(datum).filter(k=>!/(^__|_start$|_end$|sort_index)/.test(k)&&typeof datum[k]!=='object');
  const nums=keys.filter(k=>typeof datum[k]==='number'),labs=keys.filter(k=>!nums.includes(k));
  const what=labs.map(k=>datum[k]).join(' / ')||'this point';
  const val=nums.map(k=>`${k}: ${datum[k]}`).join('; ');
  const piece=`the ${what} mark`+(val?` (${val})`:'')+` on “${chartTitle}”`;
  const say=async text=>{
    el.innerHTML='<div class="note">Sending…</div>';
    try{await api('/api/say',{agent:AGENT,text:text.slice(0,800)});el.innerHTML='<div class="note">Sent to Claude.</div>';setTimeout(unpop,1200);}
    catch(e){el.textContent=e.message;}
  };
  el.innerHTML=`<div class="what">${esc(what)}<div class="note">${esc(val)}</div></div><button data-q="calc">How is this number worked out?</button><button data-q="rows">Show the rows behind it</button><button data-q="cmp">Compare it with the others</button><button data-q="wrong">This looks wrong</button><textarea aria-label="Comment" placeholder="Or write a comment about it…"></textarea><button data-q="note">Send comment</button>`;
  const questions={calc:`How is ${piece} worked out?`,rows:`Show me the rows behind ${piece}.`,cmp:`Compare ${what} with the others on “${chartTitle}”.`,wrong:`${piece} looks wrong to me. Check it.`};
  el.querySelectorAll('button').forEach(b=>b.onclick=()=>{
    if(b.dataset.q==='note'){const t=el.querySelector('textarea').value.trim();if(t)say(`About ${piece}: ${t}`);}
    else say(questions[b.dataset.q]);
  });
  el.hidden=false;document.body.classList.add('popping');
  el.style.left=Math.max(16,Math.min((ev?.clientX||40)+8,innerWidth-el.offsetWidth-16))+'px';
  el.style.top=Math.max(16,Math.min((ev?.clientY||120)+8,innerHeight-el.offsetHeight-16))+'px';
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
  document.title=v.title;$('title').textContent=v.title;await draw(v.spec,v.data,v.agent,v.title);
}).catch(e=>status(e.message,true));

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
        if(r.chart)await draw(r.chart.vega_lite,r.chart.data,r.agent,q.question);else unpop();status('Done.');
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
