import json


def read_lines(path):
    with open(path) as f:
        for line in f:
            yield line.strip()


def read_jsonl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def write_jsonl(items, path, mode='a'):
    assert mode in ['w', 'a']
    lines = [json.dumps(x) for x in items]
    with open(path, mode) as f:
        f.write('\n'.join(lines) + '\n')
        
