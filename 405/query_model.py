#!/usr/bin/env python3
import json,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for prompt in sys.argv[1:]:
    body={'model':'ctf405-home','messages':[{'role':'user','content':prompt}],
          'stream':False,'options':{'temperature':0,'seed':1,'num_predict':512,'num_ctx':4096},'keep_alive':'20m'}
    request=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=120) as response: result=json.load(response)
    print('PROMPT:',prompt,'\nRESPONSE:',result['message']['content'],flush=True)
    with (ROOT/'model_queries.jsonl').open('a') as out:
        out.write(json.dumps({'prompt':prompt,'response':result['message']['content'],'eval_count':result.get('eval_count')})+'\n')
