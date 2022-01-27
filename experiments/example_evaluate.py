from utils import read_jsonl_gz
from baselines import TextRankSummarizer
from evaluate import evaluate
from pprint import pprint
import nltk


def main():
    nltk.download("punkt", quiet=True)
    
    # download WCEP dataset beforehand
    val_data = list(read_jsonl_gz('WCEP/val.jsonl.gz'))

    textrank = TextRankSummarizer()

    settings = {
        'max_len': 40, 'len_type': 'words',
        'in_titles': False, 'out_titles': False,
        'min_sent_tokens': 7, 'max_sent_tokens': 60,
    }

    inputs = [c['articles'][:10] for c in val_data[:10]]
    ref_summaries = [c['summary'] for c in val_data[:10]]
    pred_summaries = [textrank.summarize(articles, **settings) for articles in inputs]
    results = evaluate(ref_summaries, pred_summaries)
    pprint(results)


if __name__ == '__main__':
    main()
