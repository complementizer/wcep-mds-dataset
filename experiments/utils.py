import json
import gzip
import pickle


def read_lines(path):
    with open(path) as f:
        for line in f:
            yield line


def read_json(path):
    with open(path) as f:
        object = json.loads(f.read())
    return object


def write_json(object, path):
    with open(path, 'w') as f:
        f.write(json.dumps(object))


def read_jsonl(path, load=False, start=0, stop=None):

    def read_jsonl_gen(path):
        with open(path) as f:
            for i, line in enumerate(f):
                if (stop is not None) and (i >= stop):
                    break
                if i >= start:
                    yield json.loads(line)

    data = read_jsonl_gen(path)
    if load:
        data = list(data)
    return data


def read_jsonl_gz(path):
    with gzip.open(path) as f:
        for l in f:
            yield json.loads(l)


def write_jsonl(items, path, batch_size=100, override=True):
    if override:
        with open(path, 'w'):
            pass

    batch = []
    for i, x in enumerate(items):
        if i > 0 and i % batch_size == 0:
            with open(path, 'a') as f:
                output = '\n'.join(batch) + '\n'
                f.write(output)
            batch = []
        raw = json.dumps(x)
        batch.append(raw)

    if batch:
        with open(path, 'a') as f:
            output = '\n'.join(batch) + '\n'
            f.write(output)


def load_pkl(path):
    with open(path, 'rb') as f:
        obj = pickle.load(f)
    return obj


def dump_pkl(obj, path):
    with open(path, 'wb') as f:
        pickle.dump(obj,  f)


def args_to_summarize_settings(args):
    args = vars(args)
    settings = {}
    for k in ['len_type', 'max_len',
              'min_sent_tokens', 'max_sent_tokens',
              'in_titles', 'out_titles']:
        settings[k] = args[k]
    return settings
