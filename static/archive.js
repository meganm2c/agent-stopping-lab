// Read-only presentation of the original artifacts. No generated result format.
export const paths = {
  scenarios: 'data/scenarios.json',
  sweep: 'results/phoenix-20260928T011340Z/runs.jsonl',
  final: 'results/phase3-comparison/runs.jsonl',
  summary: 'results/phase3-comparison/summary.json',
  stories: 'results/phase3-comparison/demo-traces.json',
  variation: 'results/phase3-variation/summary.json',
  repeatedRuns: 'results/phase3-variation/runs.jsonl',
  sweepSummary: 'results/phoenix-20260928T011340Z/comparison.json',
};
export const strategies = ['Fixed 2', 'Fixed 4', 'Fixed 6', 'Fixed 8', 'Adaptive'];
export const experiments = {'fixed-budget-6':'Fixed 6','fixed-budget-8':'Fixed 8','adaptive-stopping':'Adaptive'};
export const number = (value, digits=0) => value == null ? 'Unavailable' : new Intl.NumberFormat('en-US', {minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value);
export function tokens(usage={}) {
  return usage.total_token_count ?? (usage.input_token_count != null && usage.output_token_count != null ? usage.input_token_count + usage.output_token_count : null);
}
export function usage(row) {
  const agent = tokens(row.run.usage);
  const checks = (row.run.stopping_checks || []).map(check => tokens(check.usage));
  const overhead = checks.some(n => n == null) ? null : checks.reduce((a,b) => a+b,0);
  return {agent, overhead, total: agent == null || overhead == null ? null : agent + overhead};
}
export async function loadArchive(base=new URL('../',import.meta.url), fetcher=fetch) {
  const entries = await Promise.all(Object.entries(paths).map(async ([name,path]) => {
    let response;
    try { response = await fetcher(new URL(path,base)); }
    catch { throw new Error(`Could not fetch ${path}. Serve this site over HTTP and check your connection.`); }
    if (!response.ok) throw new Error(`Missing replay artifact: ${path} (HTTP ${response.status}). Restore the committed file and reload.`);
    try {
      const text = await response.text();
      return [name, path.endsWith('.jsonl') ? text.split(/\r?\n/).filter(s => s.trim()).map(s => JSON.parse(s)) : JSON.parse(text)];
    } catch { throw new Error(`Cannot read replay artifact: ${path}. Restore the committed file and reload.`); }
  }));
  return new Archive(Object.fromEntries(entries));
}
export class Archive {
  constructor(data) {
    this.scenarios = data.scenarios;
    this.summary = data.summary.aggregates;
    this.variation = Object.values(data.variation.groups);
    this.stories = data.stories;
    this.repeatedRuns = data.repeatedRuns;
    this.sweepSummary = data.sweepSummary.phoenix.all;
    this.rows = new Map(); this.byTrace = new Map();
    const add = (row,strategy,rep) => {
      const sid = row.run.scenario_id;
      const scenario = this.scenarios.find(s => s.scenario_id===sid);
      if (!scenario || scenario.runtime.user_report!==row.run.user_report) throw new Error(`Archived report does not match ${sid}.`);
      const key=JSON.stringify([sid,strategy,rep]);
      if (this.rows.has(key)) throw new Error(`Duplicate archived run: ${sid}, ${strategy}, ${rep}.`);
      this.rows.set(key,row); this.byTrace.set(row.trace_id,{sid,strategy,rep});
    };
    for (const row of data.sweep) if ([2,4].includes(row.run.configured_tool_budget)) add(row,`Fixed ${row.run.configured_tool_budget}`,1);
    for (const row of data.final) {
      const strategy = experiments[row.experiment_name];
      if (!strategy) throw new Error('Unknown strategy in final archive.');
      add(row,strategy,row.repetition);
    }
    if (this.scenarios.length!==8 || this.stories.length!==4) throw new Error('Expected eight scenarios and four curated stories.');
    for (const s of this.scenarios) for (const strategy of strategies) for (const rep of this.repetitions(strategy)) this.resolve(s.scenario_id,strategy,rep);
    for (const story of this.stories) if (!this.byTrace.has(story.trace_id)) throw new Error('A curated trace is missing from the archive.');
    const models=new Set([...this.rows.values()].map(r=>r.run.model_name));
    if(models.size!==1) throw new Error('Expected one model snapshot across the replay.');
    this.model=[...models][0];
  }
  repetitions(strategy) { return ['Fixed 2','Fixed 4'].includes(strategy) ? [1] : [1,2,3]; }
  resolve(sid,strategy,rep=1) {
    const row=this.rows.get(JSON.stringify([sid,strategy,Number(rep)]));
    if(!row) throw new Error(`Stored run not found: ${sid}, ${strategy}, repetition ${rep}.`);
    return row;
  }
  comparison() {
    return [['Accuracy','accuracy',1,true],['Evidence completeness','evidence_completeness',1,true],['Evidence sufficiency','evidence_sufficient',1,true],['Average tool calls','calls_mean',2,false],['Total tokens/run','total_tokens',0,false],['Seconds/run','latency_seconds',2,false]].map(([label,key,digits,pct]) => [label,...Object.keys(experiments).map(name=>number(this.summary[name][key]*(pct?100:1),digits)+(pct?'%':''))]);
  }
}
