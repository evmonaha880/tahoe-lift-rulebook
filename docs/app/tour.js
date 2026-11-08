/* 60-second silent tour. Open index.html?tour, press any key to start, screen-record. Captions come from the real data. */
(function(){
if(!/[?&]tour/.test(location.search)) return;
const D=window.DATA, M=window.MODEL, $=s=>document.querySelector(s);
const ln=D.strata.map(s=>s.line), lo=Math.min(...ln).toFixed(1), hi=Math.max(...ln).toFixed(1), posts=(M.agree||D.agree).posts.toLocaleString();
const css=document.createElement('style'); css.textContent=`
#cap{position:fixed;left:0;right:0;bottom:0;z-index:50;padding:22px 56px 26px;background:linear-gradient(transparent,rgba(20,12,5,.88) 38%);color:#f6ecd4;font:600 34px/1.25 "Iowan Old Style","Palatino Linotype",Georgia,serif;text-align:center;text-shadow:0 2px 6px rgba(0,0,0,.6);min-height:120px;display:flex;align-items:flex-end;justify-content:center}
#cap small{display:block;font:400 20px/1.3 ui-monospace,Menlo,monospace;letter-spacing:.14em;text-transform:uppercase;color:#e8b79a;margin-bottom:6px}
#start{position:fixed;inset:0;z-index:60;background:rgba(20,12,5,.9);color:#f6ecd4;display:flex;flex-direction:column;align-items:center;justify-content:center;font:600 40px Georgia,serif;text-align:center;gap:14px}
#start span{font:400 20px ui-monospace,Menlo,monospace;color:#e8b79a}
#endc{position:fixed;inset:0;z-index:55;background:radial-gradient(ellipse at 50% 40%,#3a2412,#150c05);color:#f6ecd4;display:none;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:18px;font-family:Georgia,serif}
#endc h1{font-size:96px;margin:0;color:#f6ecd4;text-shadow:none}#endc .s{font-size:42px;font-style:italic;color:#e8795f}#endc .u{font:400 26px ui-monospace,Menlo,monospace;color:#e8b79a;line-height:1.7}
`; document.head.appendChild(css);
const cap=document.createElement('div'); cap.id='cap'; document.body.appendChild(cap);
const st=document.createElement('div'); st.id='start'; st.innerHTML='The Liftie Sutras · 60-second tour<span>Start your screen recording, then press any key</span>'; document.body.appendChild(st);
const en=document.createElement('div'); en.id='endc'; en.innerHTML='<h1>The Liftie Sutras</h1><div class="s">Send It or End It</div><div class="u">Software archaeology for the unwritten rules of real life<br>github.com/evmonaha880/tahoe-lift-rulebook</div>'; document.body.appendChild(en);
const say=(k,t)=>{cap.innerHTML=(k?'<div><small>'+k+'</small>'+t+'</div>':'<div>'+t+'</div>');};
const go=v=>$('#nav [data-v='+v+']').click();
const sc=sel=>{const e=$(sel); if(e) e.scrollIntoView({behavior:'smooth',block:'start'});};
const pick=(id,val)=>{const e=document.getElementById(id); e.value=val; e.dispatchEvent(new Event('change'));};
const T=[
 [0,()=>{go('home');$('#v-home').scrollTop=0;say('The problem','A powder morning. The big lifts stop. Nobody says why, or for how long.');}],
 [7,()=>{sc('.story');say('The idea','The rules that stop a lift were never written down. So we dug them up.');}],
 [12,()=>{sc('.dig3');say('How we dug',posts+' posts from 8 winters of operators, matched to the weather. Three independent readers. One winter hidden at a time.');}],
 [20,()=>{sc('.tome');say('What came out','The Liftie Sutras. Wind holds begin near 60 mph. The old belief was 25.');}],
 [27,()=>{go('mountain');say('The app','Replay a real morning. Dec 16, 2024: operators held 10 lifts, and the book called 9. It never saw this winter.');}],
 [34,()=>{pick('selW','2022-23');pick('selD','2023-03-15');say('A missing page','Mar 15, 2023: 12 lifts held in light wind. No sutra explains it. We label the gap.');}],
 [41,()=>{pick('selW','2024-25');pick('selD','2024-12-16');$('[data-m=sandbox]').click();$('[data-a=ar]').click();say('Possible 2026-27','Set conditions. A warm atmospheric river, one El Niño possibility. Not a forecast.');}],
 [47,()=>{go('proof');say('The proof','Hide a winter, predict it. Eight fits, one line: '+lo+' to '+hi+' mph. It beats the 25 mph belief every winter.');}],
 [54,()=>{go('readers');say('How we checked','Every post read by our parser and two blind AI readers: Subquadratic and Meta Muse.');}],
 [58,()=>{en.style.display='flex';cap.style.display='none';}]
];
let started=false; const begin=()=>{ if(started) return; started=true; st.remove(); T.forEach(([s,f])=>setTimeout(f,s*1000)); };
document.addEventListener('keydown',begin); document.addEventListener('click',begin);
if(/[?&]auto/.test(location.search)) begin();
})();
