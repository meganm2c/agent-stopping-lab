"""Fail-closed, serial model-attempt ledger. Never infer zero usage from an error."""
import hashlib,json,re

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def audit(events,requests,transport,system,report):
    errors=[];ledger=[];active=None;attempt=0
    messages={}
    for e in events:
        if e['type']=='agent_end':
            for m in e['data']['event'].get('messages',[]):
                if m.get('role')=='assistant':
                    key=m.get('responseId') or ('error',m.get('timestamp'))
                    if key in messages and messages[key]!=m:errors.append('Conflicting assistant snapshots')
                    messages[key]=m
    used_requests=[];used_messages=[]
    expected_system=system.rstrip()+'\n\nCurrent model identity: openai/gpt-4.1-mini-2025-04-14. If asked what model you are, answer with this value for the current run.'
    for e in events:
        if e['type']=='before_agent_run':attempt+=1
        if e['type']=='model_call_started':
            if active:errors.append('Overlapping model invocations')
            active=e
        if e['type']!='model_call_ended':continue
        if not active:errors.append('End without start');continue
        start=active;active=None;s=start['data']['event'];end=e['data']['event']
        if s['callId']!=end['callId']:errors.append('Mismatched model boundaries')
        ordinal=len(ledger)+1
        canonical=f"{s['runId']}:attempt:{attempt}:invocation:{ordinal}"
        rs=[(i,r) for i,r in enumerate(requests) if start['at']<=r.get('at',-1)<=e['at']]
        ms=[(k,m) for k,m in messages.items() if start['at']<=m.get('timestamp',-1)<=e['at']]
        record={'canonical_id':canonical,'native_run_id':s['runId'],'native_call_id':s['callId'],'session_id':s.get('sessionId'),'attempt_index':attempt,'invocation_ordinal':ordinal,'start_ms':start['at'],'end_ms':e['at'],'outcome':end.get('outcome'),'requests':[],'provider_response_id':None,'usage':None}
        if len(ms)!=1:errors.append(f'{canonical}: ambiguous assistant response')
        else:
            key,m=ms[0];used_messages.append(key);record.update(provider_response_id=m.get('responseId'),usage=m.get('usage'),error_code=m.get('errorCode'))
            if m.get('stopReason')=='error':errors.append(f'{canonical}: failed invocation usage not independently attributable')
        if len(rs)!=1:errors.append(f'{canonical}: missing request or provider retries require attribution')
        for i,r in rs:
            used_requests.append(i);body=r['body'];context=[m for m in body['messages'] if m['role'] in ['system','user']]
            normalized=[]
            for m in context:
                content=m['content']
                if m['role']=='user':content=re.sub(r'^\[[A-Za-z]{3} \d{4}-\d{2}-\d{2} \d{2}:\d{2} [^\]]+\] ', '',content)
                normalized.append({'role':m['role'],'content':content})
            allowed=normalized==[{'role':'system','content':expected_system},{'role':'user','content':report}]
            tr=[t for t in transport if t['request_ordinal']==r['request_ordinal']]
            if len(tr)!=1 or tr[0].get('status')!=200:errors.append(f'{canonical}: missing or failed transport receipt')
            if not allowed:errors.append(f'{canonical}: semantic prompt drift')
            record['requests'].append({'request_ordinal':r['request_ordinal'],'canonical_request_id':canonical+f":request:{r['request_ordinal']}",'transport':tr,'effective_context_sha256':digest(context),'semantic_context_sha256':digest(normalized),'full_messages_sha256':digest(body['messages']),'allowed_context':allowed,'change_class':'allowed_timestamp_only' if allowed else 'semantic_drift'})
        ledger.append(record)
    if active:errors.append('Unclosed model invocation')
    if sorted(used_requests)!=list(range(len(requests))):errors.append('Unaccounted or multiply attributed outbound requests')
    if len(used_messages)!=len(set(used_messages)) or set(used_messages)!=set(messages):errors.append('Unaccounted or multiply attributed assistant usage')
    if not ledger:errors.append('No model invocations')
    calls=[e['data']['call'] for e in events if e['type']=='diagnostic_call']
    if [c['tool_index'] for c in calls]!=list(range(1,len(calls)+1)):errors.append('Noncanonical tool execution order')
    # Attribute every observed diagnostic execution/request to exactly one assistant tool request.
    requested=[]
    for m in messages.values():
        requested.extend((c['name'],c['arguments']) for c in m.get('content',[]) if c.get('type')=='toolCall')
    if requested!=[(c['tool_name'],c['arguments']) for c in calls]:errors.append('Tool requests and canonical execution records differ')
    return {'accepted':not errors,'errors':sorted(set(errors)),'invocations':ledger,'internal_attempts':attempt,'request_count':len(requests),'tool_record_count':len(calls),'policy':'All invocations/requests/usage attributable once; serial canonical tools; exact semantic system/user context; errors or ambiguous retry usage reject.'}
