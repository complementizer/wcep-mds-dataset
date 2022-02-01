import argparse
import multiprocessing
import json
import os
import time
import pathlib
import random
import newspaper
import json
import numpy as np


def scrape_article(url):
    a = newspaper.Article(url)
    error = None
    try:
        a.download()
        a.parse()

        if a.publish_date is None:
            time = None
        else:
            time = a.publish_date.isoformat()

        article = {
            'time': time,
            'title': a.title,
            'text': a.text,
            'url': url,
            'state': 'successful',
            'error': None,
        }
    except Exception as e:
        print(e)
        article = {
            'url': url,
            'state': 'failed',
            'error': str(e),
        }
        error = e
    return url, article, error


def write_articles(articles, path):
    lines = [json.dumps(a) for a in articles]
    with open(path, 'a') as f:
        f.write('\n'.join(lines) + '\n')


def batches(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def load_urls(path):
    urls = []
    with open(path) as f:
        for line in f:
            original_url, archive_url = line.split()
            if archive_url != 'None':
                urls.append(archive_url)
    return urls


def main(args):
    outpath = pathlib.Path(args.o)
    done_urls = set()
    failed_urls = []
    n_success = 0

    if args.override and outpath.exists():
        outpath.unlink()

    elif outpath.exists():
        with open(outpath) as f:
            for line in f:
                a = json.loads(line)
                url = a['url']
                if a['state'] == 'successful':
                    n_success += 1
                else:
                    failed_urls.append(url)
                done_urls.add(url)


    urls = load_urls(args.i)

    if args.repeat_failed:
        todo_urls = failed_urls + [url for url in urls if url not in done_urls]
    else:
        todo_urls = [url for url in urls if url not in done_urls]
    if args.shuffle:
        random.shuffle(todo_urls)

    n_done = len(done_urls)
    n_total = len(urls)
    durations = []
    t1 = time.time()

    for url_batch in batches(todo_urls, args.batchsize):

        pool = multiprocessing.Pool(processes=args.jobs)
        output = pool.map(scrape_article, url_batch)
        pool.close()

        articles = []
        for url, a, error in output:
            if a['state'] == 'successful':
                n_success += 1
                articles.append(a)
            n_done += 1
            done_urls.add(url)

        if articles:
            write_articles(articles, outpath)

        t2 = time.time()
        elapsed = t2 - t1
        durations.append(elapsed)
        t1 = t2




        print(f'{n_done}/{n_total} done')
        print(f'total: {n_total}, done: {n_done}, successful: {n_success}')

        print('TIME (seconds):')
        print('last batch:', elapsed)
        print('last 5:', np.mean(durations[-10:]))
        print('overall 5:', np.mean(durations))
        print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--i', required=True)
    parser.add_argument('--o', required=True)
    parser.add_argument('--batchsize', type=int, default=20)
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--override', action='store_true')
    parser.add_argument('--shuffle', action='store_true')
    parser.add_argument('--repeat-failed', action='store_true')
    main(parser.parse_args())