with open('output/chapter05.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, l in enumerate(lines):
    if '各ステップ' in l or '動作を実現' in l:
        print(f'{i+1}: {l.strip()}')
