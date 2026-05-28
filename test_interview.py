import urllib.request, json, os

def api(method, path, data=None):
    url = 'http://127.0.0.1:8000' + path
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {'error': str(e)}

print('=== 1. 测试面试记录列表 ===')
s, d = api('GET', '/api/interview/list')
print(f'状态: {s}')
if s == 200:
    interviews = d.get('interviews', [])
    print(f'记录数量: {len(interviews)}')
    for iv in interviews[:3]:
        iid = iv.get('interview_id', '?')
        status = iv.get('status', '?')
        name = iv.get('candidate', {}).get('name', '?')
        score = iv.get('evaluation', {}).get('overall_score', 'N/A') if iv.get('evaluation') else 'N/A'
        print(f'  - {iid} | {status} | {name} | 评分: {score}')
else:
    print(f'错误: {d}')

print()
print('=== 2. 测试获取单条记录 ===')
interviews = d.get('interviews', [])
if interviews:
    first_id = interviews[0]['interview_id']
    s, d = api('GET', f'/api/interview/detail/{first_id}')
    print(f'状态: {s}')
    if s == 200:
        iv = d.get('interview', {})
        print(f'  ID: {iv.get("interview_id")}')
        print(f'  状态: {iv.get("status")}')
        print(f'  对话数: {len(iv.get("dialogues", []))}')
        print(f'  评估: {iv.get("evaluation", {}).get("ai_comment", "N/A")[:50] if iv.get("evaluation") else "N/A"}')
    else:
        print(f'错误: {d}')

print()
print('=== 3. 测试画像列表 ===')
s, d = api('GET', '/api/interview/profiles')
print(f'状态: {s}')
if s == 200:
    profiles = d.get('profiles', [])
    print(f'画像数量: {len(profiles)}')
    for p in profiles:
        title = p.get('position', {}).get('title', '?')
        print(f'  - {p.get("_id", "?")} | {title}')
else:
    print(f'错误: {d}')

print()
print('=== 4. 测试候选人列表 ===')
s, d = api('GET', '/api/interview/candidates')
print(f'状态: {s}')
if s == 200:
    candidates = d.get('candidates', [])
    print(f'候选人数量: {len(candidates)}')
    for c in candidates:
        print(f'  - {c.get("_id", "?")} | {c.get("name", "?")}')
else:
    print(f'错误: {d}')

print()
print('=== 5. 测试启动面试 ===')
s, d = api('POST', '/api/interview/start', {'duration': 10})
print(f'状态: {s}')
if s == 200:
    iv = d.get('interview', {})
    print(f'  新面试ID: {iv.get("interview_id")}')
    print(f'  状态: {iv.get("status")}')
    print(f'  方案环节数: {len(iv.get("plan", {}).get("sections", []))}')
else:
    print(f'错误: {d.get("error", str(d))}')

print()
print('测试完成!')
