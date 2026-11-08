(function(){
const M=window.MODEL, D=window.DATA, P=M.proof;      // P: every score on the page, written by the repo pipeline (scripts/build_app_model.py from results/baselines.json)
D.strata.forEach(s=>Object.assign(s,P.strata[s.winter]));   // per-winter days, wind-hold days, scores and wind lines come from the pipeline, not from this file
const $=id=>document.getElementById(id);
const dec=s=>{const t=document.createElement('textarea');t.innerHTML=String(s);return t.value;};
const esc=s=>dec(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const GATES=['Tram','Funitel','Base to Base Gondola'];
const UPPER=M.groups.upper, LOWER=M.groups.lower, ALPINE=M.groups.alpine;   // from rules/lift_groups.json
const TIERS=[['gate','The gates',GATES],['up','Upper mountain',UPPER],['low','Lower mountain',LOWER],['alp','Alpine Meadows',ALPINE]];
const FL={day_gust:['gusts over the day','mph'],early_gust:['early-morning gusts','mph'],day_spd:['sustained wind over the day','mph'],early_spd:['early-morning wind','mph'],swe24:['snow water in 24 hours','in'],avy:['avalanche danger','of 5'],temp_base:['base temperature','F'],swe6:['snow water in 6 hours','in'],prec24s:['precipitation in 24 hours','in'],fnt_day_gust:['gusts at the Funitel top (partly estimated)','mph']};
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const dlabel=d=>{const p=d.split('-');return MON[+p[1]-1]+' '+(+p[2])+', '+p[0]};
const dayBy=date=>M.days.find(d=>d.date===date);

/* ---- the best single wind line per hidden winter is learned in scripts/baselines.py and read here ---- */
const LINE={};M.winters.forEach(w=>{ LINE[w]=P.lift[w]&&P.lift[w].wind_line_mph!=null?P.lift[w].wind_line_mph:25; });
/* ---- engine ---- */
function odds(rule,x){ if(!rule) return null; const v=x[rule.f]; if(v==null) return null; const fired=v>=rule.t; return {p:fired?rule.above:rule.below,fired,rule}; }
const NAIVE=x=>x.day_gust!=null&&x.day_gust>=25;

/* ---- state ---- */
const SL=[['day_gust','Gusts over the day','mph',0,130,1],['early_gust','Early-morning gusts','mph',0,120,1],['day_spd','Sustained wind, day','mph',0,100,1],['early_spd','Sustained wind, early','mph',0,90,1],['swe24','Snow water, 24 hours','in',0,4,0.1],['avy','Avalanche danger','of 5',0,5,1]];
const S={arch:null,mode:'replay',x:Object.assign({},M.medians),winter:'2024-25',date:'2024-12-16',tab:'home'};
const PRE=[['Calm day',{day_gust:15,early_gust:10,day_spd:8,early_spd:6,swe24:0,avy:1}],
  ['Dec 16, 2024 wind day',null,'2024-12-16'],['Dec 15, 2024 snow day',null,'2024-12-15'],
  ['Today, Nov 7 (resort closed)',{day_gust:12,early_gust:5,day_spd:4,early_spd:2,swe24:0,avy:0}]];
function setX(o){ Object.assign(S.x,o); }
function loadArch(a){ setX(a.x); S.arch=a.id; }
function loadPreset(p){ S.arch=null; const d=p[2]?(dayBy(p[2])||{x:M.feat[p[2]]}):null; setX(d?Object.fromEntries(SL.map(s=>[s[0],d.x[s[0]]??S.x[s[0]]])):p[1]); }
setX(PRE[0][1]);

/* ---- left: controls ---- */
function drawLeft(){
  let h='<h3>Mode</h3><div class="seg"><button data-m="replay" class="'+(S.mode==='replay'?'on':'')+'">Replay a day</button><button data-m="sandbox" class="'+(S.mode==='sandbox'?'on':'')+'">Set conditions</button></div>';
  if(S.mode==='sandbox'){
    h+='<h3>Conditions</h3>'+SL.map(s=>'<div class="ctl"><label>'+s[1]+'<b id="v_'+s[0]+'">'+(+S.x[s[0]]).toFixed(s[5]<1?1:0)+' '+s[2]+'</b></label><input type="range" data-k="'+s[0]+'" min="'+s[3]+'" max="'+s[4]+'" step="'+s[5]+'" value="'+S.x[s[0]]+'"></div>').join('');
    h+='<h3>Start from</h3><div class="presets">'+PRE.map((p,i)=>'<button class="chip2" data-p="'+i+'">'+p[0]+'</button>').join('')+'</div>';
    const O=D.outlook, A=(M.arch||[]), cur=A.find(a=>a.id===S.arch);
    h+='<h3>2026-27 El Niño possibilities</h3><div class="badge">2026 POSSIBILITY · NOT A FORECAST</div><div class="presets">'+A.map(a=>'<button class="chip2'+(a.id===S.arch?' sel':'')+'" data-a="'+a.id+'">'+esc(a.name)+'</button>').join('')+'</div>';
    h+=cur?'<div class="archnote"><b>'+esc(cur.name)+'.</b> '+esc(cur.blurb)+' Sliders set to the median of '+cur.n+' matching day'+(cur.n===1?'':'s')+' from the El Niño winters in our data'+(cur.n<8?' (a small sample, so treat it as illustrative)':'')+'.</div>':'<div class="archnote">'+O.lines.map(l=>'<div>'+esc(l)+'</div>').join('')+'<div style="margin-top:6px">'+esc(O.method)+'</div></div>';
    h+='<div class="note">Every lift answers with its own recovered rule. Move a slider and watch the mountain change. Rules are fitted on all eight winters.</div>';
  } else {
    h+='<h3>Winter</h3><select id="selW">'+M.winters.slice().reverse().map(w=>'<option'+(w===S.winter?' selected':'')+'>'+w+'</option>').join('')+'</select>';
    const days=M.days.filter(d=>d.winter===S.winter);
    h+='<h3>Morning</h3><select id="selD">'+days.map(d=>{const n=Object.values(d.act).filter(a=>a[0]).length;return '<option value="'+d.date+'"'+(d.date===S.date?' selected':'')+'>'+dlabel(d.date).replace(/, \d+$/,'')+' · '+n+' held</option>';}).join('')+'</select>';
    h+='<div class="nav2"><button id="prev">← Earlier</button><button id="next">Later →</button></div>';
    const d=dayBy(S.date);
    h+='<div class="readout">'+['day_gust','early_gust','day_spd','swe24','avy'].map(k=>FL[k][0]+': <b>'+(d.x[k]==null?'n/a':(+d.x[k]).toFixed(k==='swe24'?1:0)+' '+FL[k][1])+'</b>').join('<br>')+'</div>';
    h+='<div class="note">Every rule here was rebuilt from the other seven winters. This morning was never in the training data.</div>';
  }
  $('left').innerHTML=h;
  document.querySelectorAll('[data-m]').forEach(b=>b.onclick=()=>{S.mode=b.dataset.m;drawAll();});
  document.querySelectorAll('input[type=range]').forEach(r=>r.oninput=()=>{S.arch=null;S.x[r.dataset.k]=+r.value;const s=SL.find(s=>s[0]===r.dataset.k);$('v_'+r.dataset.k).textContent=(+r.value).toFixed(s[5]<1?1:0)+' '+s[2];drawCenter();drawRight();});
  document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{loadPreset(PRE[+b.dataset.p]);drawAll();});
  document.querySelectorAll('[data-a]').forEach(b=>b.onclick=()=>{loadArch((M.arch||[]).find(a=>a.id===b.dataset.a));drawAll();});
  if(S.mode==='replay'){
    $('selW').onchange=e=>{S.winter=e.target.value;const ds=M.days.filter(d=>d.winter===S.winter);S.date=ds[0].date;drawAll();};
    $('selD').onchange=e=>{S.date=e.target.value;drawAll();};
    $('prev').onclick=()=>step(-1);$('next').onclick=()=>step(1);
  }
}
function step(n){const ds=M.days.filter(d=>d.winter===S.winter);let i=ds.findIndex(d=>d.date===S.date)+n;i=Math.max(0,Math.min(ds.length-1,i));S.date=ds[i].date;drawAll();}
document.addEventListener('keydown',e=>{if(S.tab==='mountain'&&S.mode==='replay'&&!/SELECT|INPUT/.test(document.activeElement.tagName)){if(e.key==='ArrowLeft')step(-1);if(e.key==='ArrowRight')step(1);}});

/* ---- evaluate current scene ---- */
function scene(){
  const replay=S.mode==='replay', day=replay?dayBy(S.date):null, x=replay?day.x:S.x, rules=replay?(M.loo[S.winter]||{}):M.book;
  const rows=M.lifts.map(L=>{const rule=rules[L]||M.book[L]; const o=odds(rule,Object.assign({},M.medians,x)); const a=day?day.act[L]:null; return {L,rule,o,a,scheduled:replay?!!a:true};});
  return {replay,day,x,rows};
}
/* ---- center: the mountain ---- */
function drawCenter(){
  const sc=scene(); let banner='';
  const legend='<div class="legend2"><b>How to read a tile.</b> The bar and the big number are the book\'s odds of a hold: how often that lift held on past days at or past its line. The tint is what happened (red held, green ran). A call is a hold at 50% or more. <b>✓</b> the call was right, <b>✗</b> it was wrong.</div>';
  if(sc.replay){
    const live=sc.rows.filter(r=>r.a&&r.o); const H=live.filter(r=>r.a[0]).length;
    const C=live.filter(r=>r.a[0]&&r.o.p>=.5).length, FA=live.filter(r=>!r.a[0]&&r.o.p>=.5).length;
    const nq=NAIVE(sc.x), nC=nq?H:0, nFA=nq?live.filter(r=>!r.a[0]).length:0; const lq=sc.x.day_gust>=LINE[S.winter], lC=lq?H:0, lFA=lq?live.filter(r=>!r.a[0]).length:0;
    banner='<b>'+dlabel(S.date)+'.</b> Operators held <b>'+H+'</b> of '+live.length+' scheduled lifts. The book caught <b>'+C+'</b> and wrongly called a hold on <b>'+FA+'</b> that ran. One '+LINE[S.winter]+' mph wind line caught <b>'+lC+'</b> and wrongly called <b>'+lFA+'</b>. A 25 mph rule caught <b>'+nC+'</b> and wrongly called <b>'+nFA+'</b>.'+legend;
  } else {
    const n=sc.rows.filter(r=>r.o&&r.o.p>=.5).length, gate=sc.rows.filter(r=>GATES.includes(r.L)&&r.o&&r.o.p>=.5).length;
    const ar=(M.arch||[]).find(a=>a.id===S.arch); banner=(ar?'<b>Possible 2026-27 day: '+esc(ar.name)+'.</b> ':'')+'<b>'+n+'</b> of '+sc.rows.length+' lifts likely to hold.'+(gate?' <span style="color:var(--hold)">A gate lift is at risk, and most of the upper mountain follows it.</span>':' The gates look clear.')+'<div class="legend2"><b>Odds</b> = how often that lift held on past days at or past its line. Fitted on all eight winters, not held out.</div>';
  }
  let h='<div class="banner">'+banner+'</div>';
  const known=new Set();
  TIERS.forEach(([cls,lab,list])=>{
    const rs=list.map(L=>sc.rows.find(r=>r.L===L)).filter(Boolean); rs.forEach(r=>known.add(r.L)); if(!rs.length) return;
    h+='<div class="tier"><h3>'+lab+'</h3><div class="tiles">'+rs.map(r=>tile(r,sc,cls==='gate')).join('')+'</div></div>';
  });
  const rest=sc.rows.filter(r=>!known.has(r.L)); if(rest.length) h+='<div class="tier"><h3>Other</h3><div class="tiles">'+rest.map(r=>tile(r,sc,false)).join('')+'</div></div>';
  $('center').innerHTML=h;
}
function tile(r,sc,gate){
  if(sc.replay&&!r.a) return '<div class="tile na"><div class="n">'+esc(r.L)+'</div><div class="p">–</div><div class="bar"><i style="width:0"></i></div><div class="a">not on the schedule</div></div>';
  const p=r.o?r.o.p:null, pct=p==null?'–':Math.round(p*100)+'%';
  let cls='tile'+(gate?' gate':'')+(r.o&&r.o.fired?' fired':''), a='',m='';
  if(sc.replay&&r.a){ const held=r.a[0]; cls+=held?' held':' ran'; const why={w:'wind',p:'snow safety',m:'mechanical',x:'weather',u:'no cause given','':''}[r.a[1]];
    a=held?'HELD'+(why?' · '+why:''):'ran'; if(p!=null) m='<span class="m">'+((p>=.5)===!!held?'✓':'✗')+'</span>'; }
  return '<div class="'+cls+'">'+m+'<div class="n">'+esc(r.L)+'</div><div class="p">'+pct+'</div><div class="bar"><i style="width:'+(p==null?0:p*100)+'%"></i></div><div class="a">'+a+'</div></div>';
}
/* ---- right: the sutras ---- */
function drawRight(){
  const sc=scene(); let h='<h3>The sutras that apply</h3>';
  const fired=sc.rows.filter(r=>r.o&&r.o.fired&&(!sc.replay||r.a)).sort((a,b)=>b.o.p-a.o.p);
  const missedAll=sc.replay?sc.rows.filter(r=>r.a&&r.a[0]&&(!r.o||r.o.p<.5)):[];
  const missed=missedAll.filter(r=>!r.o||r.o.p<.25), near=missedAll.filter(r=>r.o&&r.o.p>=.25);
  fired.slice(0,3).forEach(r=>{
    const R=r.o.rule, fl=FL[R.f]||[R.f,''], full=M.book[r.L];
    h+='<div class="sut"><div class="h">'+esc(r.L)+'<span>'+Math.round(r.o.p*100)+'%</span></div>'+
      '<p>When '+fl[0]+' reach <b>'+Math.round(R.t)+' '+fl[1]+'</b>, it holds '+Math.round(R.above*100)+'% of days ('+Math.round(R.above*R.na)+' of '+R.na+'). Below that, '+Math.round(R.below*100)+'%.</p>'+
      '<div class="ink"><b>Ink.</b> Operators named wind on '+full.wind_days+' of its '+full.held_days+' hold days.</div>'+
      '<div class="pencil"><b>Pencil.</b> The '+Math.round(R.t)+' line was worked out from weather'+(sc.replay?', without this winter':'')+'.</div></div>';
  });
  if(fired.length>3) h+='<div class="note" style="margin-top:0">and '+(fired.length-3)+' more lifts are past their line.</div>';
  if(!fired.length&&!missed.length&&!near.length) h+='<div class="empty">No sutra applies. The chairs spin.</div>';
  else if(!fired.length) h+='<div class="empty">No sutra applies here.</div>';
  if(near.length){h+='<div class="note" style="margin:10px 0"><b>A near miss.</b> '+near.slice(0,6).map(r=>esc(r.L)+' ('+Math.round(r.o.p*100)+'%)').join(', ')+' held, just under the book\'s 50% line.</div>';}
  if(missed.length){
    const cc={};missed.forEach(r=>{const k={w:'wind',p:'snow safety',m:'mechanical',x:'weather',u:'no cause given','':'cause unknown'}[r.a[1]];cc[k]=(cc[k]||0)+1;});
    h+='<div class="torn"><b>A missing page.</b> Fewer than 1 in 4 odds, yet '+missed.length+' lift'+(missed.length===1?'':'s')+' held that no sutra called: '+missed.slice(0,6).map(r=>esc(r.L)).join(', ')+(missed.length>6?' and '+(missed.length-6)+' more':'')+'. Operators gave: '+Object.entries(cc).map(([k,v])=>v+' '+k).join(', ')+'.</div>';
  }
  if(sc.replay){
    const ps=M.posts[S.date]||[];
    h+='<h3 style="margin-top:18px">What the operators posted</h3><div class="posts">'+(ps.length?ps.slice(0,14).map(p=>'<div class="p"><div class="t">'+p[0]+'</div><div>'+esc(p[1])+'</div></div>').join('')+(ps.length>14?'<div class="note">'+(ps.length-14)+' more posts that day.</div>':''):'<div class="note">No posts found for this day.</div>')+'</div>';
  }
  $('right').innerHTML=h;
}
function drawAll(){drawLeft();drawCenter();drawRight();}

/* ---- tabs ---- */
document.querySelectorAll('#nav button').forEach(b=>b.onclick=()=>{S.tab=b.dataset.v;document.querySelectorAll('#nav button').forEach(x=>x.classList.toggle('on',x===b));document.querySelectorAll('.view').forEach(v=>v.classList.toggle('on',v.id==='v-'+S.tab));});
$('pill').textContent='rules built '+M.built+' · '+M.lifts.length+' lifts · '+M.winters.length+' winters';

/* ---- landing ---- */
(function(){ const A=M.agree||D.agree, ln=D.strata.map(s=>s.line), lo=Math.min(...ln), hi=Math.max(...ln);
  $('h_posts').textContent=A.posts.toLocaleString(); $('h_wint').textContent=M.winters.length; $('h_line').textContent=Math.round((lo+hi)/2);
  $('g1').textContent='Found in all '+M.winters.length+' winters, each time without peeking at that winter, between '+lo.toFixed(1)+' and '+hi.toFixed(1)+' mph. Each lift then has its own line.';
  document.querySelectorAll('[data-goto]').forEach(b=>b.onclick=()=>{ const t=b.dataset.goto; document.querySelector('#nav [data-v='+t+']').click(); }); })();
/* ---- dig ---- */
let sel=1;
const phaseClass=p=>p==='El Niño'?'nino':p==='La Niña'?'nina':'neutral';
function drawDig(){
  let h='',prev=null;
  D.strata.forEach((s,i)=>{ if(prev&&s.era!==prev) h+='<div class="rename">'+esc(D.renamed)+'</div>'; prev=s.era;
    h+='<div class="layer'+(i===sel?' sel':'')+'" data-i="'+i+'"><div class="name">'+s.winter+'</div><div><div class="band '+phaseClass(s.phase)+'" style="width:'+Math.max(18,Math.round(s.days/200*100))+'%"></div></div><div class="sc">'+s.score.toFixed(2)+'</div></div>'; });
  $('layers').innerHTML=h; document.querySelectorAll('.layer').forEach(el=>el.onclick=()=>{sel=+el.dataset.i;drawDig();});
  $('legend').innerHTML='<span><i style="background:#e5b47c"></i>El Niño (warm Pacific)</span><span><i style="background:#a3b9c6"></i>La Niña (cool Pacific)</span><span><i style="background:#cbc3ae"></i>neutral</span>';
  const mk=t=>{let o=esc(t);D.drift.marks.forEach(m=>{o=o.split(m).join('<mark>'+m+'</mark>');});return o;};
  $('drift').innerHTML='<h3>The rename, in the posts themselves</h3><div class="two"><div><div class="tag">'+esc(D.drift.old.date)+'</div><p>'+mk(D.drift.old.text)+'</p></div><div><div class="tag">'+esc(D.drift.new.date)+'</div><p>'+mk(D.drift.new.text)+'</p></div></div>';
  const s=D.strata[sel];
  $('find').innerHTML='<div class="tag">Artifact · '+esc(s.artifact.date)+' · '+esc(s.era)+'</div><blockquote>“'+esc(s.artifact.text)+'”</blockquote><dl><dt>Climate</dt><dd>'+esc(s.phase)+(s.strength?' ('+esc(s.strength)+')':'')+'</dd><dt>Days with posts</dt><dd>'+s.days+'</dd><dt>Wind-hold days</dt><dd>'+s.wind_holds+'</dd><dt>Score</dt><dd>'+s.score.toFixed(2)+' for the book, '+s.baseline.toFixed(2)+' for a 25 mph rule, at calling this winter\'s wind-hold days</dd></dl>';
}
/* ---- proof (computed here from held-out rules) ---- */
function drawProof(){
  const L=P.lift.pooled, book=L.per_lift_called_at_50pct, single=L.best_single_wind_line, q25=L.mph25, Pc=x=>Math.round(x*100)+'%';
  const col=(name,t,hi)=>'<div class="pc'+(hi?' hi':'')+'"><div class="pn">'+name+'</div><div class="pm"><b>'+Pc(t.precision)+'</b>of its hold calls were right</div><div class="pm"><b>'+Pc(t.recall)+'</b>of real holds caught</div><div class="pm"><b>'+t.f1.toFixed(2)+'</b>balance score</div></div>';
  const w=P.lift.winters_won_by_method, win={book:w.per_lift_called_at_50pct||0, any:w.per_lift_any_pass||0, single:w.best_single_wind_line||0, q25:w.mph25||0};
  const lines=M.winters.map(x=>P.lift[x]&&P.lift[x].wind_line_mph).filter(v=>v!=null), lo=Math.min(...lines), hi2=Math.max(...lines);
  const A=P.lift_all_named.pooled;
  $('proofnums').innerHTML='<div class="pcols">'+col('The book: each lift\'s own rule (called at 50% odds)',book,true)+col('Best single wind line, learned on the other winters ('+Math.round(lo)+' to '+Math.round(hi2)+' mph)',single,false)+col('A 25 mph rule',q25,false)+'</div><div class="cap" style="margin:-10px 0 14px"><b>Honest limit.</b> Counted on '+L.n_lift_days.toLocaleString()+' scheduled lift-days, one learned wind line scores about the same as the per-lift rules ('+single.f1.toFixed(2)+' against '+L.per_lift_any_pass.f1.toFixed(2)+' when a lift is called whenever it passes its line). Winter by winter, the best balance score goes to the 25 mph rule in '+win.q25+' winters, a single wind line in '+win.single+', the per-lift rules in '+(win.book+win.any)+' (the 25 mph rule wins only where there are very few scheduled lifts to score). A 25 mph rule wins by calling almost every windy lift a hold, which pays off only in winters with many holds. The per-lift rules\' real job is the order in which lifts go, shown on the Mountain screen. If lifts that appear only because a post named them on hold are added, every method looks better (the book '+Pc(A.per_lift_called_at_50pct.precision)+' right, a 25 mph rule '+Pc(A.mph25.precision)+'); we do not use that count because those lifts are '+'76% holds by construction. All figures: docs/RESULTS.md.</div>';
  (function(){ const ss=D.strata.slice().reverse(), W=1000,H=150,x=v=>40+(W-80)*v/100; const vals=ss.map(s=>s.line), lo=Math.min(...vals), hi=Math.max(...vals);
    let s='<svg viewBox="0 0 '+W+' '+H+'"><line x1="'+x(0)+'" y1="80" x2="'+x(100)+'" y2="80" stroke="#1d1a16" stroke-width="2"/>';
    [0,20,40,60,80,100].forEach(t=>{s+='<line x1="'+x(t)+'" y1="74" x2="'+x(t)+'" y2="86" stroke="#1d1a16"/><text x="'+x(t)+'" y="108" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" font-size="14" fill="#4a4338">'+t+' mph</text>';});
    s+='<rect x="'+x(lo)+'" y="40" width="'+Math.max(6,x(hi)-x(lo))+'" height="80" fill="#b3261e" opacity=".15"/>';
    ss.forEach((r,i)=>{ s+='<circle cx="'+x(r.line)+'" cy="'+(66-(i%2)*14)+'" r="7" fill="#b3261e" stroke="#1d1a16" stroke-width="1.5"/>'; });
    s+='<line x1="'+x(25)+'" y1="30" x2="'+x(25)+'" y2="80" stroke="#1d1a16" stroke-width="2" stroke-dasharray="5 4"/><text x="'+x(25)+'" y="22" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" font-size="14" fill="#1d1a16">the usual belief: 25</text>';
    s+='<text x="'+x((lo+hi)/2)+'" y="22" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" font-size="14" fill="#b3261e">eight hidden-winter fits: '+lo.toFixed(1)+' to '+hi.toFixed(1)+'</text></svg>';
    $('linestrip').innerHTML='<h3 style="margin-top:4px">The unwritten line, found eight times</h3>'+s+'<div class="cap">Each dot is the gust speed where wind holds begin, learned without that winter\'s data. The eight fits land within '+(hi-lo).toFixed(1)+' mph of each other.</div>'; })();
  const rows=D.strata.slice().reverse(), W=1000, rowH=46, top=14, left=100, right=60, H=top+rows.length*rowH+34, x=v=>left+(W-left-right)*v;
  let s='<svg viewBox="0 0 '+W+' '+H+'">'; [0,.2,.4,.6,.8,1].forEach(t=>{s+='<line x1="'+x(t)+'" y1="'+top+'" x2="'+x(t)+'" y2="'+(H-26)+'" stroke="#cdbf9e" stroke-dasharray="4 5"/><text x="'+x(t)+'" y="'+(H-6)+'" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" font-size="13" fill="#4a4338">'+t.toFixed(1)+'</text>';});
  rows.forEach((r,i)=>{const y=top+i*rowH+rowH/2; s+='<text x="0" y="'+(y+5)+'" font-family="ui-monospace,Menlo,monospace" font-size="15">'+r.winter+'</text><line x1="'+x(r.baseline)+'" y1="'+y+'" x2="'+x(r.score)+'" y2="'+y+'" stroke="#1d1a16" stroke-width="3"/><circle cx="'+x(r.baseline)+'" cy="'+y+'" r="8" fill="#f3ead6" stroke="#1d1a16" stroke-width="3"/><circle cx="'+x(r.score)+'" cy="'+y+'" r="9" fill="#1d1a16"/><text x="'+(x(r.score)+16)+'" y="'+(y+5)+'" font-family="ui-monospace,Menlo,monospace" font-size="14" fill="#b3261e">+'+(r.score-r.baseline).toFixed(2)+'</text>';});
  $('proof').innerHTML='<h3 style="margin-top:8px">Calling the wind-hold days of each hidden winter. Dark dot: the book. Hollow dot: a 25 mph rule.</h3>'+s+'</svg>';
  $('proofcap').textContent='Balance score is the F1 score: hits and false alarms together, 0 to 1. The lift-level numbers above cover '+L.n_lift_days.toLocaleString()+' scheduled lift-days across the hidden winters. The book is cautious: it is right far more often when it calls a hold, and it misses about '+Pc(1-book.recall)+' of real holds, many of which had no weather cause. Those are the missing pages.';
}
/* ---- readers ---- */
function drawReaders(){const R=D.readers,A=M.agree||D.agree,pct=v=>(v*100).toFixed(1).replace(/\.0$/,'')+'%',X=M.disagree;
  $('three').innerHTML='<div><div class="who">The post</div><div style="font-size:20px;font-style:italic">“'+esc(R.post)+'”</div></div><div><div class="who">Our parser</div><div class="v">'+esc(R.parser.label)+'</div><div class="c">rules we wrote</div></div><div><div class="who">Subquadratic</div><div class="v">'+esc(R.subq.label)+'</div><div class="c">sure: '+R.subq.conf.toFixed(3)+'</div></div><div><div class="who">Meta Muse</div><div class="v">'+esc(R.muse.label)+'</div><div class="c">sure: '+R.muse.conf.toFixed(3)+'</div></div>';
  $('pairs').innerHTML=[['Parser and Subquadratic',A.parser_subq],['Parser and Muse',A.parser_muse],['Subquadratic and Muse',A.subq_muse]].map(([l,v])=>'<div><b>'+pct(v)+'</b>'+l+'</div>').join('')+'<div class="cap" style="align-self:end">'+A.posts.toLocaleString()+' posts, every yes/no call. Most calls are “no,” so agreement runs high by default.</div>';
  if(X){ $('dis').innerHTML='<h3 style="margin-top:26px">Where the readers pushed back</h3><div class="big3"><div><b>'+X.posts.toLocaleString()+'</b>of '+X.of.toLocaleString()+' posts had at least one call where both readers agreed with each other and the parser differed</div></div>'+
    '<div class="exs">'+X.examples.map(e=>'<div class="ex"><div class="tag">'+esc(e.w)+' · '+esc(e.cls)+'</div><p>“'+esc(e.text)+'”</p><div class="c">Parser: <b>'+(e.parser?'yes':'no')+'</b> · both readers: <b>'+(e.readers?'yes':'no')+'</b></div></div>').join('')+'</div>'+
    '<div class="cap">These are the cases flagged for review. Some are differences in definition, such as whether a hold with a late opening also counts as a delay, so a difference is a prompt to look, not proof the parser is wrong.</div>'; }
}
drawAll();drawDig();drawProof();drawReaders();
})();
