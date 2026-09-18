import re

def search_patterns(patterns, filepath='1/main.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for pattern in patterns:
        print(f"=== Matches for pattern: {pattern} ===")
        for idx, line in enumerate(lines):
            if re.search(pattern, line):
                print(f"Line {idx+1}: {line.strip()}")
        print()

if __name__ == "__main__":
    search_patterns([r'async\s+def\s+.*activity', r'async\s+def\s+.*grev'])
