/* End-to-end test of the branded Excel export, running the REAL function
   extracted from index.html against realistic data.  Node only. */
const fs=require('fs');
const OUT='/sessions/eloquent-pensive-ramanujan/mnt/outputs';

/* ── DOM stub ───────────────────────────────────────────────────────────── */
const els={};
function mkEl(id){return els[id]||(els[id]={id,style:{},classList:{add(){},remove(){},toggle(){},contains(){return false}},
  dataset:{},value:'',textContent:'',innerHTML:'',title:'',href:'',download:'',
  setAttribute(){},getAttribute(){return null},addEventListener(){},focus(){},
  querySelector(){return mkEl('x')},querySelectorAll(){return []},appendChild(){},
  click(){captured=this;},remove(){}});}
let captured=null,blobBytes=null;
global.window={XLSX:null,addEventListener(){},location:{hash:''},matchMedia:()=>({matches:false,addEventListener(){}})};
global.document={body:{classList:{add(){},remove(){},toggle(){},contains(){return false}},appendChild(){}},
  documentElement:{},getElementById:mkEl,querySelector:()=>mkEl('q'),querySelectorAll:()=>[],
  createElement:()=>mkEl('a'+Math.random()),addEventListener(){},head:{appendChild(){}},title:''};
global.localStorage={_d:{},getItem(k){return this._d[k]||null},setItem(k,v){this._d[k]=v},removeItem(k){delete this._d[k]}};
global.navigator={onLine:true,serviceWorker:{register:()=>Promise.resolve()}};
global.location={hash:'',href:''};
global.fetch=()=>Promise.resolve({ok:true,json:()=>Promise.resolve([]),headers:{get:()=>null}});
global.Blob=function(parts){blobBytes=parts[0];};
global.URL={createObjectURL:()=>'blob:x',revokeObjectURL(){}};
global.alert=()=>{};global.confirm=()=>true;
global.setTimeout=()=>0;global.setInterval=()=>0;

/* ── load the app, exposing what the test needs ─────────────────────────── */
const html=fs.readFileSync(OUT+'/opl-quiz-fix/index.html','utf8');
const i=html.indexOf('<script>'),j=html.indexOf('</script>',i);
let src=html.slice(i+8,j);
src+="\n;module.exports={dl:downloadSkillMatrixCSV,setData:(h,q,e)=>{dashHistory=h;dashQuestions=q;dashEmployees=e;}};\n";
fs.writeFileSync('/tmp/_app_under_test.js',src);
const app=require('/tmp/_app_under_test.js');

/* ── realistic data: 99 employees, 7 days, 26 OPL ───────────────────────── */
const DEPTS=['WH','PD'],POS=['MHE Operator FG (RT&CBT)','Manual pack','Checker','SSCC Staff','Operation Supervisor'];
const refs=[];for(let n=1;n<=26;n++)refs.push('OPL-'+String(n).padStart(3,'0'));
const questions=[];let qid=0;
refs.forEach(ref=>{for(let k=0;k<3;k++)questions.push({id:'q'+(++qid),wi_reference:ref,question_th:'คำถาม '+qid,question_text:'Question '+qid});});
const employees=[];
for(let n=1;n<=99;n++)employees.push({badge_number:'MLG'+String(n).padStart(4,'0'),
  name:'Employee Number '+n,department:DEPTS[n%2],position:POS[n%5],is_manager:false});
employees.push({badge_number:'ADMIN',name:'Theo B',department:'WH',position:'Admin',is_manager:true});

let seed=42;const rnd=()=>{seed=(seed*1103515245+12345)&0x7fffffff;return seed/0x7fffffff;};
const history=[],days=[];
for(let d=6;d>=0;d--)days.push(new Date(Date.UTC(2026,8,22)-d*86400000).toISOString().slice(0,10));
days.forEach(day=>{
  employees.filter(e=>!e.is_manager).forEach(e=>{
    if(rnd()>0.93)return;
    const skill=0.5+((parseInt(e.badge_number.slice(3))*7)%45)/100;
    const pick=[];while(pick.length<3){const q=questions[Math.floor(rnd()*questions.length)];if(!pick.includes(q))pick.push(q);}
    const row={badge_number:e.badge_number,employee_name:e.name,department:e.department,quiz_date:day,total:3};
    let sc=0;
    pick.forEach((q,n)=>{const ok=rnd()<skill;if(ok)sc++;
      row['q'+(n+1)+'_id']=q.id;row['q'+(n+1)+'_correct']=ok;row['q'+(n+1)+'_answer']=ok?'A':'B';});
    row.score=sc;history.push(row);
  });
});
app.setData(history,questions,employees);

const byBadge={};history.forEach(r=>{(byBadge[r.badge_number]=byBadge[r.badge_number]||[]).push(r);});
const emp_stats=employees.filter(e=>byBadge[e.badge_number]).map(e=>{
  const rs=byBadge[e.badge_number];
  return {name:e.name,department:e.department,position:e.position,badge:e.badge_number,quizzes:rs.length,
    avg_score:Math.round(rs.reduce((s,r)=>s+r.score,0)/rs.length*100)/100,
    pass_rate_pct:Math.round(rs.filter(r=>r.score>=2).length/rs.length*100)};
}).sort((a,b)=>a.avg_score-b.avg_score);
const totalQ=history.length;
const data={analysis:{summary_stats:{total_quizzes:totalQ,
    avg_score:Math.round(history.reduce((s,r)=>s+r.score,0)/totalQ*100)/100,
    perfect_score_pct:Math.round(history.filter(r=>r.score===3).length/totalQ*100)},
  at_risk_employees:emp_stats.filter(e=>e.avg_score<2).map(e=>({name:e.name,badge:e.badge,reason:'Average score '+e.avg_score+'/3'}))},
  emp_stats,period_label:'16 – 22 September 2026'};

(async()=>{
  await app.dl(data,days[0],days[days.length-1]);
  if(!blobBytes)throw new Error('no file produced');
  fs.writeFileSync(OUT+'/e2e.xlsx',Buffer.from(blobBytes));
  console.log('rows',history.length,'· employees',emp_stats.length,
              '· at-risk',data.analysis.at_risk_employees.length,
              '·',(blobBytes.length/1024).toFixed(0),'KB ·',captured&&captured.download);
  process.exit(0);
})();
