import requests
import argparse
import pathlib
from bs4 import BeautifulSoup

ROOT_URL = 'https://en.wikipedia.org/wiki/Portal:Current_events'


def extract_month_urls():
    html = requests.get(ROOT_URL).text
    soup = BeautifulSoup(html, 'html.parser')
    e = soup.find('div', class_='NavContent hlist')
    urls = [x['href'] for x in e.find_all('a')]
    urls = [url for url in urls if url.count('/') == 3]
    urls = ['https://en.wikipedia.org' + url for url in urls]
    return urls


def main(args):
    out_dir = pathlib.Path(args.o)
    if not out_dir.exists():
        out_dir.mkdir()

    month_urls = extract_month_urls()
    print(f'Storing {len(month_urls)} WCEP month pages:')

    for url in month_urls:
        print(url)
        fname = url.split('/')[-1] + '.html'
        html = requests.get(url).text
        fpath = out_dir / fname
        with open(fpath, 'w') as f:
            f.write(html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--o', type=str, help='output directory', required=True)
    main(parser.parse_args())
