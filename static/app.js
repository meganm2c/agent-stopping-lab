import {renderOpenClaw} from './openclaw.js';
import {loadArchive, strategies, number, usage, tokens} from './archive.js';
const $ = id => document.getElementById(id);
const escape = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const yes = value => value ? 'Yes' : 'No';
const codes = items => items.length ? items.map(e=>`<code>${escape(e)}</code>`).join(', ') : 'None';
const phoenixMetrics = new Set(['Diagnosis','Accuracy','Evidence completeness','Evidence sufficient','Evidence sufficiency','Premature stop','Premature stops','Post-sufficiency calls','False early stop','Adaptive stop triggered','Stop reason']);
function metricLabel(value) {
  return phoenixMetrics.has(value) ? `<strong class="phoenix-capability">${escape(value)}</strong>` : escape(value);
}
function table(rows,headers=null) {
  return `<div class="table-wrap"><table>${headers?`<thead><tr>${headers.map(h=>`<th scope="col">${metricLabel(h)}</th>`).join('')}</tr></thead>`:''}<tbody>${rows.map(([label,...values])=>`<tr><th scope="row">${metricLabel(label)}</th>${values.map(v=>`<td>${escape(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function evidence(row) {
  const m=row.metrics;
  const observed=row.run.evidence_ids_retrieved;
  const required=[...m.required_evidence_retrieved,...m.missing_required_evidence];
  return `<div class="evidence"><p class="note">Required/missing evidence labels are post-hoc evaluation annotations. The runtime agent did not know these labels.</p><div class="evidence-grid"><div><h4>Observed evidence</h4>${codes(observed)}</div><div><h4>Required evidence</h4>${codes(required)}</div><div><h4>Missing required evidence</h4>${codes(m.missing_required_evidence)}</div></div></div>`;
}
function snapshots(index,rows=[]) {
  const views=[
    [['budget-evals','Budget-limited investigation: Phoenix experiment evaluations for diag_007, Fixed-2. Diagnosis correctness is 0, evidence completeness is 0.25, and premature stop is 1. The underlying trace view currently has a Phoenix rendering error; this is the evaluation view for the same recorded run.']],
    [['evidence-evals','Correctness and evidence are separate evaluations: diag_008, Adaptive, repetition 1. Phoenix shows diagnosis_correct = 1, evidence_sufficient = 0, and premature_stop = 1. Its displayed completeness score is truncated to 0.66; the stored value is 4/6 (66.7%).']],
    [['repeat-a','diag_007, Fixed-6, repetition 1: the final tool checks the recent API change and retrieves api_change.'],['repeat-b','diag_007, Fixed-6, repetition 4: the final tool reads database logs and retrieves database_logs instead. Compare these with the recorded paths above.']],
    [['adaptive-stop','diag_004, Adaptive, repetition 3: the selected stopping_check returns STOP after the second tool result. Read its reason alongside the available API observation and the missing evidence listed above.']],
  ];
  return `<section class="phoenix-snapshots"><h3>Phoenix screenshots</h3><p class="note">Captured from the saved experiments. Select an image to open it at full size.</p>${views[index].map(([name,caption])=>`<figure class="snapshot"><a href="static/screenshots/${name}.png" target="_blank" rel="noopener noreferrer"><img src="static/screenshots/${name}.png" alt="${escape(caption)}" loading="lazy"></a><figcaption>${escape(caption).replace(/diagnosis_correct|evidence_sufficient|premature_stop/g, term=>`<strong class="phoenix-capability">${term}</strong>`)}</figcaption></figure>`).join('')}<p class="note">${rows.map(r=>`Trace ID: <code>${escape(r.trace_id)}</code>`).join('<br>')}</p></section>`;
}
function replay(row,strategy,rep) {
  const {run,metrics:m}=row;
  const counts=usage(row);
  const checks=run.stopping_checks || [];
  const source=['Fixed 2','Fixed 4'].includes(strategy)?'Phoenix fixed-budget sweep · one run per scenario/budget':'Final repeated Phase 3 comparison · three runs per scenario/strategy';
  const steps=run.tool_calls.map(call=>{
    const out=call.output;
    const check=checks.find(c=>c.tool_index===call.tool_index);
    return `<li class="step"><h3>${call.tool_index}. <code>${escape(call.tool_name)}(${escape(call.arguments.component)})</code></h3>
      ${!call.executed?'<p>Execution blocked.</p>':''}
      ${out.status?`<p><strong>Status:</strong> ${escape(out.status)}</p>`:''}
      ${'changed' in out?`<p><strong>Recent change:</strong> ${yes(out.changed)}</p>`:''}
      ${['detail','log_summary','description','error'].filter(k=>out[k]).map(k=>`<p>${escape(out[k])}</p>`).join('')}
      ${out.evidence_id?`<p><strong>Evidence returned:</strong> <code>${escape(out.evidence_id)}</code></p>`:''}
      ${check?`<aside class="check"><strong class="phoenix-capability">Stopping check — ${escape(check.decision)}</strong><p>${escape(check.reason)}</p><p class="note">Controller: ${number(check.elapsed_seconds,2)}s · ${number(tokens(check.usage))} tokens</p></aside>`:''}</li>`;
  }).join('');
  const reason={tool_budget:'Budget-forced final answer',agent_answered:'Voluntary answer',adaptive_stop:'Adaptive controller STOP'}[run.stop_reason] || run.stop_reason;
  const rows=[['Diagnosis',m.diagnosis_correct?'Correct':'Incorrect'],['Evidence completeness',number(m.evidence_completeness*100,1)+'%'],['Evidence sufficient',yes(m.evidence_sufficient)],['Tool calls',run.number_of_tool_calls],['Total latency',number(run.elapsed_seconds,2)+'s'],['Agent tokens',number(counts.agent)],['Total tokens',number(counts.total)],['Stop reason',reason],['Post-sufficiency calls',m.excess_calls],['Premature stop',yes(m.premature_stop)]];
  if(checks.length) {
    const stopped=run.adaptive_stop_call_index!=null;
    rows.push(['Adaptive stop triggered',yes(stopped)],['Stopping call index',stopped?run.adaptive_stop_call_index:'Not triggered'],['False early stop',yes(stopped&&!m.evidence_sufficient)],['Stopper overhead',`${number(counts.overhead)} tokens; ${number(checks.reduce((s,c)=>s+c.elapsed_seconds,0),2)}s`]);
  }
  return `<article class="report"><span class="badge">${escape(strategy)} · Run ${rep}</span><h2>User report</h2><p>${escape(run.user_report)}</p><p class="note">${source}</p></article>
    <h2>Ordered trajectory</h2><p class="note">Observed tool results and controller decisions, in execution order.</p><ol class="trajectory">${steps||'<li>No tool calls recorded.</li>'}</ol>
    <article class="result"><h2>Final result</h2><p class="note">Evaluation below was applied after execution. These labels were hidden from the agent and controller.</p>
    <p><strong>Predicted root cause:</strong> <code>${escape(run.final_diagnosis.predicted_root_cause)}</code></p><p>${escape(run.final_diagnosis.explanation)}</p>${table(rows)}
    ${evidence(row)}<p><strong>Required evidence retrieved:</strong> ${codes(m.required_evidence_retrieved)}</p><p><strong>Required evidence missing:</strong> ${codes(m.missing_required_evidence)}</p>
    <p class="note">Evidence sufficiency is a fixed rubric; a correct label can still lack supporting evidence. Total tokens and latency include stopping checks.</p></article>`;
}
const stories=[
  ['Budget-limited investigation','In this two-call trace, frontend and API status lead to api_dependency_issue. The budget forces an answer before API logs, database status, and the API change can distinguish the actual cause.'],
  ['Correct diagnosis with incomplete evidence','The model named the right root cause, but gathered only 4/6 required items (66.7%). Cache logs and the cache change were still missing. Correctness is true; evidence sufficiency is false; premature stop is true.'],
  ['Repeated runs with different tool sequences','These two Fixed-6 runs both diagnosed database_connection_regression. One inspected the API change; the other read database logs. They made the same number of calls, but ended with different evidence completeness, tokens, and latency. The variation does not by itself establish a model failure. It shows why diagnosis accuracy and tool-path consistency should be evaluated separately.'],
  ['Adaptive stop before evidence sufficiency','The controller accepted slow API reads as a coherent explanation and stopped before database health and cache evidence were checked. The agent then named the wrong cause. The STOP decision and missing evidence show where the investigation ended relative to the evidence rubric.'],
];
function repeatedPair(archive) {
  const pick=rep=>archive.repeatedRuns.find(r=>r.run.scenario_id==='diag_007' && r.run.configured_tool_budget===6 && r.repetition===rep);
  const pair=[pick(1),pick(4)];
  if(pair.some(r=>!r)) throw new Error('Missing diag_007 Fixed-6 repeatability examples.');
  if(pair[0].run.final_diagnosis.predicted_root_cause!==pair[1].run.final_diagnosis.predicted_root_cause) throw new Error('Repeatability story requires matching recorded diagnoses.');
  return pair;
}
function trajectoryPair(pair) {
  return `<p class="note">Targeted repeatability study · diag_007 · Fixed-6 · repetitions 1 and 4 of five. These are not final-comparison runs.</p><p><strong>User report:</strong> ${escape(pair[0].run.user_report)}</p><div class="two-col trajectory-pair">${pair.map((row,i)=>`<article class="report"><h3>Run ${i===0?'A':'B'} · repetition ${row.repetition}</h3><ol class="path-list">${row.run.tool_calls.map(c=>`<li><code>${escape(c.tool_name)}(${escape(c.arguments.component)})</code><span>Observed: ${escape(c.output.evidence_id)}</span></li>`).join('')}<li>Answer: <code>${escape(row.run.final_diagnosis.predicted_root_cause)}</code></li></ol><p class="note">Evaluation after execution</p>${table([['Diagnosis',row.metrics.diagnosis_correct?'Correct':'Incorrect'],['Tool calls',row.run.number_of_tool_calls],['Evidence completeness',number(row.metrics.evidence_completeness*100,1)+'%'],['Evidence sufficient',yes(row.metrics.evidence_sufficient)],['Tokens',number(usage(row).total)],['Latency',number(row.run.elapsed_seconds,2)+'s'],['Stop reason',row.run.stop_reason]])}${evidence(row)}</article>`).join('')}</div>`;
}
function options(control,items,value) {
  control.replaceChildren(...items.map(([label,key])=>new Option(label,key)));
  if(value!=null) control.value=String(value);
}
function showError(error) {
  $('status').hidden=false; $('status').dataset.error='true';
  $('status').textContent=error.message; $('demo').hidden=true;
}
try {
  await renderOpenClaw({table, escape, number});
  const archive=await loadArchive();
  options($('scenario'),archive.scenarios.map(s=>[`${s.scenario_id} — ${s.runtime.user_report}`,s.scenario_id]),'diag_004');
  options($('strategy'),strategies.map(s=>[s,s]),'Fixed 8');
  const updateReplay=()=>{
    try { $('replay').innerHTML=replay(archive.resolve($('scenario').value,$('strategy').value,$('repetition').value),$('strategy').value,Number($('repetition').value)); }
    catch(error){showError(error);}
  };
  const reset=()=>{
    const reps=archive.repetitions($('strategy').value);
    options($('repetition'),reps.map(r=>[String(r),r]),1); $('repetition').disabled=reps.length===1;
    updateReplay();
  };
  $('scenario').addEventListener('change',reset); $('strategy').addEventListener('change',reset); $('repetition').addEventListener('change',updateReplay); reset();
  const fixed=archive.summary['fixed-budget-8'],adaptive=archive.summary['adaptive-stopping'];
  $('comparison').innerHTML=table(archive.comparison(),['Metric','Fixed-6','Fixed-8','Adaptive'])+`<aside class="callout"><h3>Fewer tool calls did not mean a more efficient system.</h3><p>Adaptive used <strong>${number(100*(1-adaptive.calls_mean/fixed.calls_mean),1)}% fewer tool calls</strong> than Fixed-8, but <strong>${number(100*(adaptive.total_tokens/fixed.total_tokens-1),1)}% more total tokens</strong> and <strong>${number(100*(adaptive.latency_seconds/fixed.latency_seconds-1),1)}% more time</strong>.</p><p><strong>${Math.round(adaptive.false_early_stop*adaptive.n)} of ${adaptive.n} runs stopped without sufficient evidence.</strong></p><p>The controller added a model inference after each tool result. It often accepted a plausible intermediate explanation before resolving the cause. Reliability fell while total cost increased. The frozen hypothesis was not supported; the prompt was not tuned after the results.</p></aside>`;
  options($('story'),stories.map(([title],i)=>[title,i]),0);
  const pair=repeatedPair(archive);
  const storyRows=[archive.resolve('diag_007','Fixed 2',1),archive.resolve('diag_008','Adaptive',1),null,(()=>{const r=archive.byTrace.get(archive.stories[3].trace_id);return archive.resolve(r.sid,r.strategy,r.rep);})()];
  const updateStory=()=>{
    const i=Number($('story').value);
    const row=storyRows[i];
    const body=i===2?trajectoryPair(pair):replay(row,i===0?'Fixed 2':'Adaptive',row.repetition||1);
    $('story-replay').innerHTML=`<h3>${escape(stories[i][0])}</h3>${body}<aside class="callout"><h3>Interpretation</h3><p>${escape(stories[i][1])}</p></aside>${snapshots(i,i===2?pair:[row])}`;
  };
  $('story').addEventListener('change',updateStory); updateStory();
  $('repeatability').innerHTML=`<h3><strong class="phoenix-capability">Repeated-run trajectory analysis</strong></h3><p>The targeted repeatability study found stable diagnoses within all <strong>${archive.variation.filter(g=>g.diagnosis_consistency===1).length} of ${archive.variation.length} scenario/budget groups</strong>, while <strong>${archive.variation.filter(g=>g.trajectory_variants>1).length} of ${archive.variation.length}</strong> used varying tool trajectories. Equivalent final labels can hide different evidence paths, calls, tokens, latency, and stopping.</p>`;
  $('overview-variation').innerHTML=$('repeatability').innerHTML+'<p>Two correct answers can differ in ordering, calls, evidence, redundant investigation, stopping behavior, latency, and tokens. The baseline Phoenix trace analysis below shows the actual pair.</p>';
  $('scenario-examples').innerHTML='<ul>'+archive.scenarios.map(s=>`<li><code>${escape(s.scenario_id)}</code> — “${escape(s.runtime.user_report)}”</li>`).join('')+'</ul>';
  const hard=archive.scenarios.find(s=>s.scenario_id==='diag_007');
  const easy=archive.scenarios.find(s=>s.scenario_id==='diag_001');
  $('scenario-design').innerHTML=`<div class="two-col"><article class="report"><h4>Quickly discriminating evidence · ${escape(easy.scenario_id)}</h4><p>“${escape(easy.runtime.user_report)}”</p><p>${escape(easy.runtime.components.api.status.detail)}</p><p>This observation can directly support the diagnosis.</p></article><article class="report"><h4>A plausible symptom can mislead · ${escape(hard.scenario_id)}</h4><p>“${escape(hard.runtime.user_report)}”</p><p>Frontend degraded → API waiting downstream → database status healthy → cache healthy. These are the scenario's early status observations, not a claim that the low-budget run saw all four.</p><p>Surface interpretation: API dependency problem.</p><details><summary>After-the-fact explanation of the scenario design</summary><p>Ground truth: <code>${escape(hard.root_cause)}</code>.</p><p>${escape(hard.runtime.components.api.logs.log_summary)}</p><p>${escape(hard.runtime.components.api.recent_change.description)}</p><p class="note">Ground truth is shown here for teaching; it was hidden during execution.</p></details></article></div>`;
  $('sweep-results').innerHTML=table(Object.entries(archive.sweepSummary).map(([budget,r])=>[budget,number(100*r.accuracy,1)+'%',number(100*r.avg_evidence_completeness,1)+'%',number(r.avg_tool_calls,2),number(100*r.premature_stop_rate,1)+'%']),['Tool budget','Accuracy','Evidence completeness','Average calls','Premature stops']);
  $('learning-cost').textContent=`Adaptive reduced calls by ${number(100*(1-adaptive.calls_mean/fixed.calls_mean),1)}% versus Fixed-8, but increased total tokens by ${number(100*(adaptive.total_tokens/fixed.total_tokens-1),1)}% and latency by ${number(100*(adaptive.latency_seconds/fixed.latency_seconds-1),1)}%. Compare the full system, including the controller.`;
  $('model').textContent=archive.model;
  $('status').hidden=true; $('demo').hidden=false;
} catch(error) {showError(error);}
const tabs=[...document.querySelectorAll('[role=tab]')];
function activate(tab) {
  for(const item of tabs) {
    const selected=item===tab;
    item.setAttribute('aria-selected',String(selected)); item.tabIndex=selected?0:-1;
    $(item.getAttribute('aria-controls')).hidden=!selected;
  }
}
for(const [i,tab] of tabs.entries()) {
  tab.addEventListener('click',()=>activate(tab));
  tab.addEventListener('keydown',event=>{
    const next={ArrowRight:(i+1)%tabs.length,ArrowLeft:(i+tabs.length-1)%tabs.length,Home:0,End:tabs.length-1}[event.key];
    if(next!=null){event.preventDefault();activate(tabs[next]);tabs[next].focus();}
  });
}
document.addEventListener('error',event=>{
  const img=event.target;
  if(!(img instanceof HTMLImageElement)) return;
  const notice=document.createElement('p');notice.className='note';notice.textContent='Screenshot unavailable. Restore the image file to view this Phoenix capture.';
  (img.closest('a') || img).replaceWith(notice);
},true);

for(const link of document.querySelectorAll('[data-story]')) {
  link.addEventListener('click',()=>{
    $('story').value=link.dataset.story;
    $('story').dispatchEvent(new Event('change'));
    activate($('tab-baseline'));
    $('story').focus();
  });
}

// Cache same-origin static assets for later offline reloads. Never cache APIs.
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js').catch(() => {
    // Replay remains usable online when hosting disallows service workers.
  });
}
