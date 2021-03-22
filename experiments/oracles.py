import argparse
from collections import Counter
from nltk import word_tokenize, ngrams
from summarizer import Summarizer
import utils


def compute_rouge_n(hyp, ref, rouge_n=1, tokenize=True):
    hyp_words = word_tokenize(hyp) if tokenize else hyp
    ref_words = word_tokenize(ref) if tokenize else ref

    if rouge_n > 1:
        hyp_items = list(ngrams(hyp_words, n=rouge_n))
        ref_items = list(ngrams(ref_words, n=rouge_n))
    else:
        hyp_items = hyp_words
        ref_items = ref_words

    if len(hyp_items) == 0 or len(ref_items) == 0:
        return {'p': 0., 'r': 0., 'f': 0.}

    hyp_counts = Counter(hyp_items)
    ref_counts = Counter(ref_items)

    match = 0
    for tok in hyp_counts:
        match += min(hyp_counts[tok], ref_counts[tok])

    prec_denom = sum(hyp_counts.values())
    if match == 0 or prec_denom == 0:
        precision = 0
    else:
        precision = match / prec_denom

    rec_denom = sum(ref_counts.values())
    if match == 0 or rec_denom == 0:
        recall = 0
    else:
        recall = match / rec_denom

    if precision == 0 or recall == 0:
        fscore = 0
    else:
        fscore = 2 * precision * recall / (precision + recall)

    return {'p': precision, 'r': recall, 'f': fscore}


class Oracle():
    def __init__(self, rouge_n=1, metric='f', early_stopping=True):
        self.rouge_n = rouge_n
        self.metric = metric
        self.early_stopping = early_stopping
        self.summarizer = Summarizer()

    def summarize(self,
                  ref,
                  articles,
                  max_len,
                  len_type,
                  in_titles,
                  out_titles,
                  min_sent_tokens,
                  max_sent_tokens):
        articles = self.summarizer._preprocess(articles)
        sents = [s for a in articles for s in a.sents]
        sents = self.summarizer._deduplicate(sents)
        if in_titles == False or out_titles == False:
            sents = [s for s in sents if not s.is_title]
        sent_lens = [self.summarizer._sent_len(s, len_type) for s in sents]
        current_len = 0
        remaining = list(range(len(sents)))
        selected = []
        scored_selections = []
        ref_words = word_tokenize(ref)

        while current_len < max_len and len(remaining) > 0:
            scored = []
            current_summary_words = [
                tok for i in selected for tok in sents[i].words
            ]
            for i in remaining:
                new_len = current_len + sent_lens[i]
                if new_len <= max_len:
                    try:
                        summary_words = current_summary_words + sents[i].words
                        rouge_scores = compute_rouge_n(
                            summary_words,
                            ref_words,
                            rouge_n=self.rouge_n,
                            tokenize=False
                        )
                        score = rouge_scores[self.metric]
                        scored.append((i, score))
                    except:
                        pass
            if len(scored) == 0:
                break
            scored.sort(key=lambda x: x[1], reverse=True)
            best_idx, best_score = scored[0]
            scored_selections.append((selected + [best_idx], best_score))
            current_len += sent_lens[best_idx]
            selected.append(scored[0][0])
            remaining.remove(best_idx)

        if self.early_stopping == False:
            # remove shorter summaries
            max_sents = max([len(x[0]) for x in scored_selections])
            scored_selections = [x for x in scored_selections
                                 if len(x[0]) < max_sents]


        scored_selections.sort(key=lambda x: x[1], reverse=True)
        if len(scored_selections) == 0:
            return ''
        best_selection = scored_selections[0][0]
        summary_sents = [sents[i].text for i in best_selection]
        return ' '.join(summary_sents)


class SingleOracle():
    def __init__(self, rouge_n=1, metric='f', early_stopping=True):
        self.rouge_n = rouge_n
        self.metric = metric
        self.oracle = Oracle(rouge_n, metric, early_stopping)

    def summarize(self,
                  ref,
                  articles,
                  max_len,
                  len_type,
                  in_titles,
                  out_titles,
                  min_sent_tokens,
                  max_sent_tokens):
        scored_oracles = []
        for a in articles:
            summary = self.oracle.summarize(
                ref, [a], max_len, len_type, in_titles, out_titles,
                min_sent_tokens, max_sent_tokens
            )
            rouge_scores = compute_rouge_n(
                summary,
                ref,
                rouge_n=self.rouge_n,
                tokenize=True
            )
            score = rouge_scores[self.metric]
            scored_oracles.append((summary, score))
        scored_oracles.sort(key=lambda x: x[1], reverse=True)
        return scored_oracles[0][0]


class LeadOracle():
    def __init__(self, rouge_n=1, metric='f'):
        self.rouge_n = rouge_n
        self.metric = metric
        self.summarizer = Summarizer()

    def summarize(self,
                  ref,
                  articles,
                  max_len,
                  len_type,
                  in_titles,
                  out_titles,
                  min_sent_tokens,
                  max_sent_tokens):

        articles = self.summarizer._preprocess(articles)
        scored_summaries = []
        for a in articles:
            selected_sents = []
            current_len = 0
            sents = a.sents
            if in_titles == False or out_titles == False:
                sents = [s for s in sents if not s.is_title]
            for s in sents:
                l = self.summarizer._sent_len(s, len_type)
                new_len = current_len + l
                if new_len <= max_len:
                    selected_sents.append(s.text)
                    current_len = new_len
                if new_len > max_len:
                    break
            if len(selected_sents) >= 1:
                summary = ' '.join(selected_sents)
                rouge_scores = compute_rouge_n(
                    summary,
                    ref,
                    self.rouge_n,
                    tokenize=True
                )
                score = rouge_scores[self.metric]
                scored_summaries.append((summary, score))
        scored_summaries.sort(key=lambda x: x[1], reverse=True)
        summary = scored_summaries[0][0]
        return summary


def main(args):
    if args.mode == 'predict-lead-oracle':
        summarizer = LeadOracle(
            rouge_n=args.rouge_n,
            metric=args.metric
        )
    elif args.mode == 'predict-oracle':
        summarizer = Oracle(
            rouge_n=args.rouge_n,
            metric=args.metric
        )
    elif args.mode == 'predict-oracle-single':
        summarizer = SingleOracle(
            rouge_n=args.rouge_n,
            metric=args.metric
        )
    else:
        raise ValueError('Unknown or unspecified --mode: ' + args.mode)

    summarize_settings = utils.args_to_summarize_settings(args)
    Summarizer.summarize_dataset(
        summarizer,
        dataset_path=args.dataset,
        pred_path=args.preds,
        summarize_settings=summarize_settings,
        start=args.start,
        stop=args.stop,
        batchsize=args.batchsize,
        jobs=args.jobs,
        oracle=True
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode')
    parser.add_argument('--dataset')
    parser.add_argument('--preds')
    parser.add_argument('--start', type=int, default=-1)
    parser.add_argument('--stop', type=int, default=-1)
    parser.add_argument('--max-len', type=int, default=40)
    parser.add_argument('--len-type', default='words')
    parser.add_argument('--in-titles', action='store_true')
    parser.add_argument('--out-titles', action='store_true')
    # min/max sent tokens have no effect for oracles
    parser.add_argument('--min-sent-tokens', type=int, default=7)
    parser.add_argument('--max-sent-tokens', type=int, default=60)
    parser.add_argument('--rouge-n', type=int, default=1)
    parser.add_argument('--metric', default='f')
    parser.add_argument('--batchsize', type=int, default=32)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--early-stopping', action='store_true')
    main(parser.parse_args())
