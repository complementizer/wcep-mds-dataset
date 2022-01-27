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

    for c in val_data[:5]:
        print("ARTICLE HEADLINES:")
        articles = c["articles"][:10]
        for a in articles:
            print(a["title"])
        summary = textrank.summarize(articles, **settings)
        print()
        print("SUMMARY:")
        print(summary)
        print("="*100)


if __name__ == '__main__':
    main()
