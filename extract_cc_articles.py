import argparse
import pathlib
import logging
import json
import subprocess
import multiprocessing
import newspaper
import sys
import time
from warcio.archiveiterator import ArchiveIterator


def read_warc_gz(path):
    with open(path, 'rb') as f:
        for record in ArchiveIterator(f):
            # records are queries followed by response, we only need response
            if record.content_type == 'application/http; msgtype=response':
                yield record


def get_record_id(record):
    id = record.rec_headers.get_header('WARC-Record-ID')
    id = id.split('uuid:')[1].split('>')[0]
    return id


def get_record_url(record):
    return record.rec_headers.get_header('WARC-Target-URI')


def download_cc_file(cc_path, local_cc_path):
    aws_path = f's3://commoncrawl/{cc_path}'
    cmd = f'aws s3 cp {aws_path} {local_cc_path} --no-sign-request'
    logging.debug(cmd)
    cmd = cmd.split()
    while not local_cc_path.exists():
        p = subprocess.Popen(cmd)
        try:
            p.wait()
        except KeyboardInterrupt:
            p.terminate()
        if local_cc_path.exists():
            break
        logging.info(f'file download failed, retrying: {cc_path}')
        time.sleep(5)


def read_lines(path):
    with open(path) as f:
        for line in f:
            yield line.strip()


def read_jsonl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def read_article_ids(path):
    id_to_collection = {}
    ids = set()
    for cluster in read_jsonl(path):
        for a in cluster['cc_articles']:
            ids.add(a['id'])
            id_to_collection[a['id']] = cluster['collection']
    return ids, id_to_collection


def extract_article(item):
    html = item['html']
    extracted = newspaper.Article(item['url'])
    try:
        extracted.download(input_html=html)
        extracted.parse()

        if extracted.publish_date is None:
            time = None
        else:
            time = extracted.publish_date.isoformat()

        article = {
            'id': item['id'],
            'cc_file': item['cc_file'],
            'time': time,
            'title': extracted.title,
            'text': extracted.text,
            'url': item['url'],
            'collection': item['collection'],
        }

    except Exception as e:
        logging.error(f'record-id: {item["id"]}, error:{e}')
        article = None
    return article


def process_batch(items, out_path, jobs):
    logging.debug('extracting articles...')
    pool = multiprocessing.Pool(processes=jobs)
    try:
        articles = pool.map(extract_article, items)
        articles = [a for a in articles if a is not None]
        pool.close()
        logging.debug('extracting articles done')
    except KeyboardInterrupt:
        pool.terminate()
        sys.exit()
    write_jsonl(articles, out_path, mode='a')
    new_record_ids = [x['id'] for x in items]
    logging.info(f'done-record-ids:{" ".join(new_record_ids)}')
    return articles


def write_jsonl(items, path, mode='a'):
    lines = [json.dumps(x) for x in items]
    with open(path, mode) as f:
        f.write('\n'.join(lines) + '\n')


def parse_logged_record_ids(line):
    ids = line.split('done-cc-ids:')[1]
    ids = ids.split()
    return set(ids)


def parse_logged_cc_file(line):
    return line.split('done-cc-file:')[1].strip()


def read_log(path):
    done_cc_files = set()
    done_record_ids = set()
    with open(path) as f:
        for line in f:
            if 'done-cc-file' in line:
                done_cc_files.add(parse_logged_cc_file(line))
            elif 'done-cc-ids' in line:
                done_record_ids |= parse_logged_record_ids(line)
    return done_cc_files, done_record_ids


def mute_other_loggers():
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('newspaper').setLevel(logging.WARNING)
    logging.getLogger('chardet.charsetprober').setLevel(logging.WARNING)


def main(args):
    storage = pathlib.Path(args.storage)
    logpath = storage / 'log.txt'
    cc_files_path = storage / 'cc_files.txt'
    out_path = storage / 'cc_articles.jsonl'

    if not storage.exists():
        storage.mkdir()

    if args.override and out_path.exists():
        out_path.unlink()
    if args.override and logpath.exists():
        logpath.unlink()

    logging.basicConfig(
        level=logging.DEBUG,
        filename=logpath,
        filemode=('w' if args.override else 'a'),
        format='%(asctime)s %(levelname)-8s %(message)s'
    )
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    mute_other_loggers()

    if logpath.exists():
        done_cc_files, done_record_ids = read_log(logpath)
    else:
        done_cc_files, done_record_ids = set(), set()

    cc_files = list(read_lines(cc_files_path))
    todo_record_ids, id_to_collection = read_article_ids(args.dataset)
    n_files = len(cc_files)

    for i, cc_file in enumerate(cc_files):
        if cc_file in done_cc_files:
            continue

        logging.debug(f'file {i+1}/{n_files}')

        local_cc_path = storage / cc_file.split('/')[-1]
        if not local_cc_path.exists():
            download_cc_file(cc_file, local_cc_path)

        batch = []
        n_found_articles = 0
        for i, record in enumerate(read_warc_gz(local_cc_path)):
            if i % 10000 == 0:
                logging.debug(
                    f'{i} records checked, {n_found_articles} articles found')
            id = get_record_id(record)
            if id in todo_record_ids:
                n_found_articles += 1
                item = {
                    'id': id,
                    'html': record.content_stream().read(),
                    'url': get_record_url(record),
                    'collection': id_to_collection[id],
                    'cc_file': cc_file
                }
                batch.append(item)

            if len(batch) >= args.batchsize:
                process_batch(batch, out_path, args.jobs)
                batch = []

        if batch:
            process_batch(batch, out_path, args.jobs)

        logging.info(f'done-cc-file:{cc_file}')
        local_cc_path.unlink()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--storage', required=True)
    parser.add_argument('--override', action='store_true')
    parser.add_argument('--batchsize', type=int, default=1000)
    parser.add_argument('--jobs', type=int, default=4)
    main(parser.parse_args())
