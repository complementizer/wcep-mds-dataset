import argparse
import datetime
import calendar
import pathlib
import collections
import arrow
import json
import uuid
from bs4 import BeautifulSoup


def make_month_to_int():
    month_to_int = {}
    for i, month in enumerate(calendar.month_name):
        if i > 0:
            month_to_int[month] = i
    return month_to_int


EVENTS = []
TOPIC_TO_SUB = collections.defaultdict(set)
TOPIC_TO_SUPER = collections.defaultdict(set)
EVENT_ID_COUNTER = 0
MONTH_TO_INT = make_month_to_int()


class Event:
    def __init__(self, text, id, date, category=None, stories=None,
                 wiki_links=None, references=None):

        # print(f'[{date}] {text}')
        # print(stories)
        # for url in references:
        #     print(url)
        # print()
        self.text = text
        self.id = id
        self.date = date
        self.category = category
        self.stories = stories if stories else []
        self.wiki_links = wiki_links if wiki_links else []
        self.references = references if references else []

    def to_json_dict(self):
        return {
            'text': self.text,
            'id': self.id,
            'date': str(self.date),
            'category': self.category,
            'stories': self.stories,
            'wiki_links': self.wiki_links,
            'references': self.references,
        }


def url_to_time(url, month_to_num):
    tail = url.split('/')[-1]
    month, year = tail.split('_')
    m = month_to_num[month]
    y = int(year)
    return datetime.datetime(year=y, month=m, day=1)


def extract_date(date_div):
    date = date_div.find('span', class_='summary')
    date = date.text.split('(')[1].split(')')[0]
    date = arrow.get(date)
    date = datetime.date(date.year, date.month, date.day)
    return date


def wiki_link_to_id(s):
    return s.split('/wiki/')[1]


def recursively_extract_bullets(e,
                                date,
                                category,
                                prev_stories,
                                is_root=False):
    global EVENT_ID_COUNTER
    if is_root:
        lis = e.find_all('li', recursive=False)
        result = [recursively_extract_bullets(li, date, category, [])
                  for li in lis]
        return result
    else:
        ul = e.find('ul')
        if ul:
            # intermediate "node", e.g. a story an event is assigned to

            links = e.find_all('a', recursive=False)
            new_stories = []
            for link in links:
                try:
                    new_stories.append(wiki_link_to_id(link.get('href')))
                except:
                    print("not a wiki link:", link)
            lis = ul.find_all('li', recursive=False)

            for prev_story in prev_stories:
                for new_story in new_stories:
                    TOPIC_TO_SUB[prev_story].add(new_story)
                    TOPIC_TO_SUPER[new_story].add(prev_story)

            stories = prev_stories + new_stories
            for li in lis:
                recursively_extract_bullets(li, date, category, stories)

        else:
            # reached the "leaf", i.e. event summary
            text = e.text
            wiki_links = []
            references = []
            for link in e.find_all('a'):
                url = link.get('href')
                if link.get('rel') == ['nofollow']:
                    references.append(url)
                elif url.startswith('/wiki'):
                    wiki_links.append(url)
            event = Event(text=text, id=EVENT_ID_COUNTER, date=date,
                          category=category, stories=prev_stories,
                          wiki_links=wiki_links, references=references)
            EVENTS.append(event)
            EVENT_ID_COUNTER += 1


def process_month_page_2004_to_2017(html):
    soup = BeautifulSoup(html, 'html.parser')
    days = soup.find_all('table', class_='vevent')
    for day in days:
        date = extract_date(day)
        #print('DATE:', date)
        category = None
        desc = day.find('td', class_='description')
        for e in desc.children:
            if e.name == 'dl':
                category = e.text
            elif e.name == 'ul':
                recursively_extract_bullets(e, date, category, [], is_root=True)


def process_month_page_from_2018(html):
    soup = BeautifulSoup(html, 'html.parser')
    days = soup.find_all('div', class_='vevent')
    for day in days:
        date = extract_date(day)
        #print('DATE:', date)
        category = None
        desc = day.find('div', class_='description')
        for e in desc.children:
            if e.name == 'div' and e.get('role') == 'heading':
                category = e.text
                #print('-'*25, 'CATEGORY:', category, '-'*25, '\n')
            elif e.name == 'ul':
                recursively_extract_bullets(e, date, category, [], is_root=True)


def file_to_date(path):
    fname = str(path.name)
    month, year = fname.split('.')[0].split('_')
    month = MONTH_TO_INT[month]
    year = int(year)
    date = datetime.date(year, month, 1)
    return date


def main(args):
    in_dir = pathlib.Path(args.i)
    for fpath in sorted(in_dir.iterdir(), key=file_to_date):
        fname = fpath.name

        with open(fpath) as f:
            html = f.read()

        year = int(fname.split('.')[0].split('_')[1])

        if 2004 <= year < 2018:

            print(fname)
            process_month_page_2004_to_2017(html)

        elif 2018 <= year :
            print(fname)
            process_month_page_from_2018(html)

        EVENTS.sort(key=lambda x: x.date)

    with open(args.o, 'w') as f:
        for e in EVENTS:
            e_json = json.dumps(e.to_json_dict())
            f.write(e_json + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--i', type=str, help='input directory', required=True)
    parser.add_argument('--o', type=str, help='output file', required=True)
    main(parser.parse_args())