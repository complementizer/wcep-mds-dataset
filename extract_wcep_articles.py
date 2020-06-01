import argparse
import multiprocessing
import time
import pathlib
import random
import newspaper
import json
import numpy as np
import utils


def extract_article(todo_article):
    url = todo_article['archive_url']
    extracted = newspaper.Article(url)
    try:
        extracted.download()
        extracted.parse()

        if extracted.publish_date is None:
            time = None
        else:
            time = extracted.publish_date.isoformat()

        article = {
            'time': time,
            'title': extracted.title,
            'text': extracted.text,
            'url': todo_article['url'],
            'archive_url': url,
            'collection': todo_article['collection'],
            'state': 'successful',
            'error': None,
        }

    except Exception as e:
        print(e)
        article = {
            'archive_url': url,
            'state': 'failed',
            'error': str(e),
        }

    return article


def batches(iterable, n=1):
    l = len(iterable)
    for i in range(0, l, n):
        yield iterable[i:min(i + n, l)]


def read_input(path):
    articles = []
    with open(path) as f:
        for line in f:
            cluster = json.loads(line)
            for a in cluster['wcep_articles']:
                a['collection'] = cluster['collection']
                articles.append(a)
    return articles


def main(args):

    outpath = pathlib.Path(args.o)
    done_urls = set()
    failed_articles = []
    n_done = 0
    n_success = 0

    if args.override and outpath.exists():
        outpath.unlink()

    elif outpath.exists():
        with open(outpath) as f:
            for line in f:
                a = json.loads(line)
                url = a['archive_url']
                if a['state'] == 'successful':
                    n_success += 1
                else:
                    failed_articles.append(a)
                n_done += 1
                done_urls.add(url)

    todo_articles = read_input(args.i)
    n_total = len(todo_articles)
    todo_articles = [a for a in todo_articles if a['archive_url']
                     not in done_urls]

    print('failed articles from last run:', len(failed_articles))
    print('articles todo:', len(todo_articles))


    if args.repeat_failed:
        todo_articles = failed_articles + todo_articles

    if args.shuffle:
        random.shuffle(todo_articles)

    durations = []
    t1 = time.time()
    for todo_batch in batches(todo_articles, args.batchsize):

        pool = multiprocessing.Pool(processes=args.jobs)
        output = pool.map(extract_article, todo_batch)
        pool.close()

        articles = []
        for a in output:
            if a['state'] == 'successful':
                n_success += 1
                articles.append(a)
                done_urls.add(a['archive_url'])
            n_done += 1

        if articles:
            utils.write_jsonl(articles, outpath, mode='a')

        t2 = time.time()
        elapsed = t2 - t1
        durations.append(elapsed)
        t1 = t2

        print(f'{n_done}/{n_total} done, {n_success}/{n_done} successful')
        print('Average per-batch time (seconds):')
        print('last batch:', elapsed)
        print('last 10:', np.mean(durations[-10:]))
        print('overall:', np.mean(durations))
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
