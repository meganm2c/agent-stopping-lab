// Synthetic offline contract examples, not captured requests or measured results.
export const requests = Array.from({length: 4}, () => ({
  blocked: false,
  body: {
    model: 'gpt-4.1-mini-2025-04-14', temperature: 0, parallel_tool_calls: false,
    tools: ['check_status', 'read_logs', 'check_recent_change'].map(name => ({function: {name}})),
    messages: [{role: 'user', content: 'Offline diagnostic incident'}],
  },
}));
export const run = {
  calls: [{executed: true}, {executed: true}, {executed: false}],
  finalDiagnosis: {predicted_root_cause: 'api_configuration_issue'},
  stopReason: 'stop', actualRuntime: 'openclaw',
  assistantMessages: Array.from({length: 4}, () => ({usage: {totalTokens: 10}})),
  usage: {total: 40},
};
