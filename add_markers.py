import os

def add_marker(directory, marker):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith('test_') and file.endswith('.py') or file == 'perf_database.py':
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if f'pytest.mark.{marker}' not in content:
                    content = f'import pytest\n\npytestmark = pytest.mark.{marker}\n\n' + content
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)

add_marker('tests/unit', 'unit')
add_marker('tests/integration', 'integration')
add_marker('tests/performance', 'performance')
