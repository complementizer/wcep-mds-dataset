import argparse
import json
import pathlib
import shutil
from collections import defaultdict


def read_jsonl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)


def write_jsonl(items, path, mode='w'):
    assert mode in ['w', 'a']
    lines = [json.dumps(x) for x in items]
    with open(path, mode) as f:
        output = '\n'.join(lines) + '\n'
        f.write(output)


def split_dataset(outdir, tmp_clusters_path):
    print('splitting dataset into train/val/test...')
    for i, c in enumerate(read_jsonl(tmp_clusters_path)):
        if i % 1000 == 0:
            print(i, 'clusters done')
        outpath = outdir / (c['collection'] + '.jsonl')
        write_jsonl([c], outpath, mode='a')


def cleanup_clusters(path, tmp_path):
    print('cleaning up:', path.name)
    for i, c in enumerate(read_jsonl(path)):
        if i % 1000 == 0:
            print(i, 'clusters done')
        articles = []
        if 'wcep_articles_filled' in c:
            for a in c['wcep_articles_filled']:
                a['origin'] = 'WCEP'
                articles.append(a)
        if 'cc_articles_filled' in c:
            for a in c['cc_articles_filled']:
                a['origin'] = 'CommonCrawl'
                articles.append(a)

        c = {
            'id': c['id'],
            'date': c['date'],
            'summary': c['summary'],
            'articles': articles,
            'collection': c['collection'],
            'wiki_links': c['wiki_links'],
            'reference_urls': c['reference_urls'],
            'category': c['category']
        }

        write_jsonl([c], tmp_path, mode='a')

    shutil.move(tmp_path, path)


def get_article_to_cluster_mappings(clusters):
    url_to_cluster_idxs = defaultdict(list)
    id_to_cluster_idx = {}
    for i, c in enumerate(clusters):
        for a in c['wcep_articles']:
            url_to_cluster_idxs[a['archive_url']].append(i)
        for a in c['cc_articles']:
            id_to_cluster_idx[a['id']] = i
    return url_to_cluster_idxs, id_to_cluster_idx


def add_wcep_articles_to_clusters(wcep_path, url_to_cluster_idxs, clusters):
    print('adding articles from WCEP to clusters')
    for a in read_jsonl(wcep_path):
        for i in url_to_cluster_idxs[a['archive_url']]:
            c = clusters[i]
            c.setdefault('wcep_articles_filled', [])
            c['wcep_articles_filled'].append(a)


def add_cc_articles_to_clusters(clusters, cc_path, id_to_cluster_idx, tmp_articles_path):
    print('adding articles from CommonCrawl to clusters')
    n_clusters = len(clusters)
    n_clusters_done = 0
    for i, a in enumerate(read_jsonl(cc_path)):
        if i % 10000 == 0:
            print(f'{i} cc articles done, {n_clusters_done}/{n_clusters} clusters done')
        cluster_idx = id_to_cluster_idx[a['id']]
        c = clusters[cluster_idx]
        c.setdefault('cc_articles_filled', [])
        c['cc_articles_filled'].append(a)

        if len(c['cc_articles']) == len(c['cc_articles_filled']):
            write_jsonl([c], tmp_articles_path, mode='a')
            clusters[cluster_idx] = None
            n_clusters_done += 1
    print(f'{i} cc articles done, {n_clusters_done}/{n_clusters} clusters done')


def main(args):
    outdir = pathlib.Path(args.o)
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir()
    tmp_clusters_path = outdir / 'tmp_clusters.jsonl'
    if tmp_clusters_path.exists():
        tmp_clusters_path.unlink()

    # get article -> cluster mappings
    clusters = list(read_jsonl(args.dataset))
    url_to_cluster_idxs, id_to_cluster_idx = get_article_to_cluster_mappings(
        clusters
    )

    # add articles from WCEP to clusters, using URLs
    add_wcep_articles_to_clusters(
        args.wcep_articles, url_to_cluster_idxs, clusters
    )

    # add articles from CommonCrawl to clusters, using IDs
    add_cc_articles_to_clusters(
        clusters, args.cc_articles, id_to_cluster_idx, tmp_clusters_path
    )

    # split clusters into separate train/val/test files
    split_dataset(outdir, tmp_clusters_path)
    tmp_clusters_path.unlink()

    for fn in ['train.jsonl', 'val.jsonl', 'test.jsonl']:
        cleanup_clusters(outdir / fn, tmp_clusters_path)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', required=True)
    parser.add_argument('--wcep-articles', required=True)
    parser.add_argument('--cc-articles', required=True)
    parser.add_argument('--o', required=True)
    main(parser.parse_args())