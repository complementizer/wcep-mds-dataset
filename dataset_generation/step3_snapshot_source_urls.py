import argparse
import savepagenow
import json
import os
import random
import time
from requests.exceptions import ConnectionError


def read_jsonl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


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


def main(args):
    n_done = 0
    n_captured = 0
    n_success = 0
    done_url_set = set()
    if not args.override and os.path.exists(args.o):
        with open(args.o) as f:
            for line in f:
                url, archive_url = line.split()
                n_done += 1
                if archive_url != 'None':
                    n_success += 1
                done_url_set.add(url)

    events = read_jsonl(args.i)
    urls = [url for e in events for url in e['references']
            if url not in done_url_set]
    if args.shuffle:
        random.shuffle(urls)
    n_total = len(urls) + len(done_url_set)

    batch = []
    for url in urls:

        repeat = True
        archive_url, captured = None, None
        while repeat:
            try:
                archive_url, captured = savepagenow.capture_or_cache(url)
                repeat = False
                if captured:
                    n_captured += 1
                n_success += 1
            except Exception as e:
                if isinstance(e, ConnectionError):
                    print('Too many requests, waiting a bit...')
                    repeat = True
                else:
                    repeat = False
            if repeat:
                time.sleep(60)
            else:
                time.sleep(1)

            if archive_url is not None:
                batch.append((url, archive_url, captured))
        n_done += 1

        print(f'total: {n_total}, done: {n_done}, '
              f'successful: {n_success}, captured: {n_captured}\n')

        if len(batch) < args.batchsize:
            lines = [f'{url} {archive_url}' for (url, archive_url, _) in batch]
            if len(lines) > 0:
                with open(args.o, 'a') as f:
                    f.write('\n'.join(lines) + '\n')
            batch = []


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--i', required=True)
    parser.add_argument('--o', required=True)
    parser.add_argument('--batchsize', type=int, default=20)
    parser.add_argument('--override', action='store_true')
    parser.add_argument('--shuffle', action='store_true')
    main(parser.parse_args())
