import re
import sys

def check_js_syntax(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract script content
    scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)
    for i, script in enumerate(scripts):
        try:
            compile(script, f'script_{i}', 'exec')
            print(f"Script {i} syntax OK")
        except SyntaxError as e:
            print(f"Script {i} syntax ERROR: {e}")
            # Print lines around error
            lines = script.split('\n')
            start = max(0, e.lineno - 5)
            end = min(len(lines), e.lineno + 5)
            for idx in range(start, end):
                print(f"{idx+1}: {lines[idx]}")

if __name__ == "__main__":
    check_js_syntax('admin.html')
