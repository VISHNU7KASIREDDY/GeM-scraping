import os
import re
import tokenize
import io
def clean_python_code(code_str):
    out = []
    tokens = tokenize.generate_tokens(io.StringIO(code_str).readline)
    last_lineno = -1
    last_col = 0
    for tok in tokens:
        tok_type = tok[0]
        tok_string = tok[1]
        start_line, start_col = tok[2]
        end_line, end_col = tok[3]
        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out.append(" " * (start_col - last_col))
        if tok_type == tokenize.COMMENT:
            pass 
        elif tok_type == tokenize.STRING:
            cleaned_s = re.sub(r'[^\x00-\x7F\u20B9\xA0]', '', tok_string)
            out.append(cleaned_s)
        else:
            out.append(tok_string)
        last_lineno = end_line
        last_col = end_col
    res = "".join(out)
    res = "\n".join([line for line in res.splitlines() if line.strip() != ""])
    return res
def clean_markdown_code(content):
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    content = re.sub(r'[^\x00-\x7F\u20B9\xA0\u2014\u2022\u2192]', '', content)
    return content
if __name__ == '__main__':
    project_dir = '/Users/vishnukasireddy/GeM-scraping'
    for root, dirs, files in os.walk(project_dir):
        if 'venv' in root or '.git' in root or 'output' in root or '.pytest_cache' in root:
            continue
        for file in files:
            filepath = os.path.join(root, file)
            if file.endswith('.py'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        code = f.read()
                    cleaned = clean_python_code(code)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(cleaned)
                    print(f"Cleaned {filepath}")
                except Exception as e:
                    print(f"Failed to clean {filepath}: {e}")
            elif file.endswith('.md'):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    cleaned = clean_markdown_code(content)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(cleaned)
                    print(f"Cleaned {filepath}")
                except Exception as e:
                    print(f"Failed to clean {filepath}: {e}")