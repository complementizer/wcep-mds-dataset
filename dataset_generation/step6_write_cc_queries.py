import argparse
import collections
import spacy
from general import utils

def main(args):
    events = utils.read_jsonl(args.i)
    date_to_queries = collections.defaultdict(list)
    for e in events:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--i', required=True)
    main(parser.parse_args())