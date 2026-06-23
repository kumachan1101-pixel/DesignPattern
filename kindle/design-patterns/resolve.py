import re

with open('output/chapter09_2.md', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'<<<<<<< HEAD\n.*?\n=======\n(.*?)\n>>>>>>> [^\n]*\n', r'\1\n', text, flags=re.DOTALL)

with open('output/chapter09_2.md', 'w', encoding='utf-8') as f:
    f.write(text)
