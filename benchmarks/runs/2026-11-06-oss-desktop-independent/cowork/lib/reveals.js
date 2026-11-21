'use strict';
const when=t=>{const d=new Date(t);return isNaN(d)?'':d.toLocaleString('en-IN',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});};
const REVEAL_WS=new URLSearchParams(location.search).get('ws')||'';
const outcomes={approved:'Allowed.',denied:'Kept hidden.',timeout:'This request expired. The value stays hidden.',budget:'No reveals left. You can allow 3 more on the Reveals page.',changed:'The file changed. The value stays hidden.'};
function decisionLabel(decision){status(outcomes[decision]||'Waiting for your choice.');document.querySelectorAll('#request button').forEach(b=>b.disabled=decision!=='pending');}
if(location.pathname==='/consent') (async()=>{
  $('ledger').href=link('/reveals?ws='+encodeURIComponent(REVEAL_WS));
  try{
    const r=await api('/api/consent?id='+encodeURIComponent(ID));
    const lookup=r.kind==='lookup',many=!lookup&&Array.isArray(r.values)&&r.values.length;
    $('title').textContent=lookup?'Claude asks to search the web with a masked value':many?'Claude asks to see one column':'Claude asks to see a masked value';
    $('intro').textContent=lookup?'Claude will not see the value. The search is sent from this computer to Google News and Wikipedia.':many?`All ${r.values.length} values in this column will be shared with Claude. This uses one reveal.`:'Only this value will be shared with Claude.';
    const where=r.column+' ('+r.file.replace(/^drive\//,'').replace(/\.[^.]+$/,'')+')';
    $('details').innerHTML=(many?[['Column',where],['Values',r.values.map(v=>v.value).join(', ')],['Reason',r.reason]]:[['Code',r.code],['Column',where],['Real value',r.value],['Reason',r.reason]]).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('');
    $('search').textContent=lookup?'Search: '+r.query.replaceAll('{value}',r.value):'';
    $('approve').textContent=lookup?'Allow search':'Reveal to Claude';$('request').hidden=false;decisionLabel(r.decision);
    let done=r.decision!=='pending';
    const choose=async approve=>{
      document.querySelectorAll('#request button').forEach(b=>b.disabled=true);
      try{const out=await api('/api/consent',{id:ID,approve});done=true;decisionLabel(out.decision);}
      catch(e){status(e.message,true);document.querySelectorAll('#request button').forEach(b=>b.disabled=false);}
    };
    $('approve').onclick=()=>choose(true);$('deny').onclick=()=>choose(false);
    const timer=setInterval(async()=>{if(done){clearInterval(timer);return;}try{const out=await api('/api/consent?id='+encodeURIComponent(ID));if(out.decision!=='pending'){done=true;decisionLabel(out.decision);}}catch(e){status('Could not check this request. Try opening it again.',true);}},1000);
  }catch(e){status('This request could not open. Return to Claude to try again.',true);}
})();
if(location.pathname==='/reveals'){
  async function refresh(){
    const r=await api('/api/reveals?ws='+encodeURIComponent(REVEAL_WS));
    $('budget').textContent=REVEAL_WS?r.remaining+' reveals left in this workspace.':'Open this page from a Drivey workspace to allow more reveals.';
    $('more').disabled=!REVEAL_WS;
    $('items').innerHTML=r.items.length?r.items.map((v,i)=>`<section class="card" data-kind="${v.kind==='lookup'?'lookup':'unmask'}"><h2>${esc(v.code)}: ${esc(v.value)}</h2><p>${v.kind==='lookup'?'Search allowed. Value kept hidden from Claude.':'Revealed to Claude.'}</p><p>${esc(v.column)} (${esc(v.file)})</p><p>${esc(v.reason)}</p><p class="dim">${esc(when(v.at))}</p><button data-hide="${i}">Hide again</button></section>`).join(''):'<p>No values have been revealed.</p>';
    document.querySelectorAll('[data-hide]').forEach(b=>b.onclick=async()=>{try{await api('/api/reveals/hide',r.items[Number(b.dataset.hide)]);await refresh();status('Hidden.');}catch(e){status(e.message,true);}});
    status('');
  }
  $('more').onclick=async()=>{try{await api('/api/reveals/more',{workspace:REVEAL_WS});await refresh();status('Allowed 3 more.');}catch(e){status(e.message,true);}};
  refresh().catch(e=>status('Reveals could not open. Try again.',true));
}
