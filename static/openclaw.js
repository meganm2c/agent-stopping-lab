// Curated report facts only. No inference, eval recomputation or Phoenix requests.
export async function renderOpenClaw({table, escape, number}) {
  const response = await fetch(new URL('./openclaw.json', import.meta.url));
  if (!response.ok) throw new Error('Missing static/openclaw.json');
  const data = await response.json();
  if (data.accepted !== 20 || data.examples.length !== 3) throw new Error('Invalid static/openclaw.json');
  const $ = id => document.getElementById(id);
  $('oc-results').innerHTML = table(data.by_budget.map(r => [r.budget,`${r.accuracy}%`,`${r.completeness}%`,`${r.sufficient}%`,`${r.premature}%`,number(r.calls,1)]), ['Tool budget','Accuracy','Evidence completeness','Evidence sufficient','Premature stop','Avg calls']);
  $('oc-cost').innerHTML = table(data.by_budget.map(r => [r.budget,number(r.diagnostic_tokens,1),number(r.finalizer_tokens,1),number(r.total_tokens,1),number(r.diagnostic_s,2)+'s',number(r.finalization_s,2)+'s',number(r.trace_s,2)+'s']), ['Tool budget','Diagnostic tokens','Finalizer tokens','Total tokens','Diagnostic latency','Finalization latency','Total trace']);
  function card(r) {
    return `<article class="report"><h3>${escape(r.scenario)} · budget ${r.budget} · repetition ${r.repetition}</h3><p class="note">Source trace ID: <code>${escape(r.trace_id)}</code></p><ol class="path-list">${r.sequence.map(c=>`<li><code>${escape(c)}</code></li>`).join('')}</ol><p><strong>Final diagnosis:</strong> <code>${escape(r.diagnosis)}</code> (correct)</p>${table([['Executed calls',r.calls],['Blocked requests',r.blocked],['Evidence completeness',number(r.completeness,1)+'%'],['Evidence sufficient',r.sufficient?'Yes':'No'],['Diagnostic tokens',number(r.tokens[0])],['Finalizer tokens',number(r.tokens[1])],['Total tokens',number(r.tokens[2])],['Diagnostic latency',number(r.latency[0],3)+'s'],['Finalization latency',number(r.latency[1],3)+'s'],['Total trace',number(r.latency[2],3)+'s'],['Full wall time',number(r.latency[3],3)+'s']])}<p><strong>Evidence retrieved:</strong> ${r.evidence.map(x=>`<code>${escape(x)}</code>`).join(', ')}</p><p><strong>Required evidence missing:</strong> ${escape(r.missing)}</p><p class="note">Evaluations were applied after execution. This report extract contains ordered calls, not the full model transcript.</p></article>`;
  }
  const selector=$('oc-selector');
  selector.replaceChildren(...data.examples.map((r,i)=>new Option(`${r.scenario} · budget ${r.budget} · repetition ${r.repetition}`,i)));
  const update=()=>{$('oc-replay').innerHTML=card(data.examples[Number(selector.value)]);};
  selector.addEventListener('change',update);update();
  $('oc-pair').innerHTML=data.examples.filter(r=>r.budget===8).map(card).join('');
}
