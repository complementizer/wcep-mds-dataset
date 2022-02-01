import argparse
from general import utils


def load_urls(path):
    url_to_arc = {}
    arc_to_url = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                url, arc_url = parts
                url_to_arc[url] = arc_url
                arc_to_url[arc_url] = url
    return url_to_arc, arc_to_url


def main(args):

    articles = list(utils.read_jsonl(args.articles))
    events = list(utils.read_jsonl(args.events))

    url_to_arc, arc_to_url = load_urls(args.urls)

    url_to_article = {}
    for a in articles:
        arc_url = a['url']
        if arc_url in arc_to_url:
            url = arc_to_url[arc_url]
            url_to_article[url] = a
            a['archive_url'] = arc_url
            a['url'] = url

    new_events = []
    for e in events:

        e_urls = e['references']
        e_articles = [url_to_article[url]
                      for url in e_urls if url in url_to_article]
        e['articles'] = e_articles

        if len(e_articles) > 0:
            new_events.append(e)

    print('original events:', len(events))
    print('new events:', len(new_events))
    utils.write_jsonl(new_events, args.o)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--articles', required=True)
    parser.add_argument('--events', required=True)
    parser.add_argument('--urls', required=True)
    parser.add_argument('--o', required=True)
    main(parser.parse_args())
