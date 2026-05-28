import json

with open(r'D:\实习\human_analysis\data\interviews\index.json', encoding='utf-8') as f:
    data = json.load(f)

interviews = data.get('interviews', [])
print(f'总记录数: {len(interviews)}')
print()

# 分析状态分布
statuses = {}
for iv in interviews:
    st = iv.get('status', '未知')
    statuses[st] = statuses.get(st, 0) + 1
print('状态分布:', statuses)
print()

# 检查已完成记录的对话情况
completed = [iv for iv in interviews if iv.get('status') == '已完成']
print(f'已完成: {len(completed)} 条')
for iv in completed[:5]:
    iid = iv.get('interview_id', '?')
    dialogues = iv.get('dialogues', [])
    eval_data = iv.get('evaluation', {})
    score = eval_data.get('overall_score', 'N/A') if eval_data else 'N/A'
    gen_by = iv.get('plan', {}).get('_generated_by', 'N/A')
    print(f'  {iid} | 对话:{len(dialogues)} | 评分:{score} | 生成:{gen_by}')

print()

# 检查进行中的记录
in_progress = [iv for iv in interviews if iv.get('status') == '进行中']
print(f'进行中: {len(in_progress)} 条')
for iv in in_progress:
    iid = iv.get('interview_id', '?')
    dialogues = iv.get('dialogues', [])
    print(f'  {iid} | 对话:{len(dialogues)}')

# 检查单个记录文件
import os
records_dir = r'D:\实习\human_analysis\data\interviews\records'
files = os.listdir(records_dir)
print(f'\nrecords 目录文件数: {len(files)}')
print(f'示例文件: {files[:3]}')
