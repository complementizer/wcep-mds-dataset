import argparse
import unittest
import time
import arrow
import json
import datetime
import os
import pathlib
import ccrawl


def get_text_selectolax(html):
    tree = HTMLParser(html)

    if tree.body is None:
        return None

    for tag in tree.css('script'):
        tag.decompose()
    for tag in tree.css('style'):
        tag.decompose()

    text = tree.body.text(separator='\n')
    return text


class Query:
    def __init__(self, all_words, any_words, date):
        self.all_words = all_words
        self.any_words = any_words
        self.date = date

    @staticmethod
    def load(s):
        d = json.loads(s)
        all_words = d['all_words']
        any_words = d['any_words']
        date = arrow.get(d['date']).date()
        q = Query(all_words, any_words, date)
        return q

    @staticmethod
    def load_queries(path):
        queries = []
        with open(path) as f:
            for line in f:
                q = Query.load(line)
                queries.append(q)
        return queries

    def matches(self, html):
        pass


def main(args):

    file_stream = cc.CCDumpStream(args.storage)
    outfile = open(args.o, 'wb')
    warc_writer = WARCWriter(outfile)
    queries = Query.load_queries(args.q)

    for fpath in file_stream.files(args.i):
        date = file_stream.get_file_date(fpath)
        active_queries = [q for q in queries if q.date == date]

        for record in WarcIO.read_warc_gz(fpath):
            html = record.content_stream().read()

            for q in active_queries:
                if q.matches(html):
                    WarcIO.reload_record(record, html)
                    warc_writer.write_record(record)
                    break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--i', required=True)
    parser.add_argument('--q', required=True)
    parser.add_argument('--storage', required=True)
    parser.add_argument('--o', required=True)
    main(parser.parse_args())