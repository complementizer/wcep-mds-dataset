import argparse
import collections
import numpy as np
import utils
from newsroom.analyze.rouge import ROUGE_L, ROUGE_N


def print_mean(results, rouge_types):
    for rouge_type in rouge_types:
        precs = results[rouge_type]['p']
        recalls = results[rouge_type]['r']
        fscores = results[rouge_type]['f']
        p = round(np.mean(precs), 3)
        r = round(np.mean(recalls), 3)
        f = round(np.mean(fscores), 3)
        print(rouge_type, 'p:', p, 'r:', r, 'f:', f)


def evaluate(ref_summaries, pred_summaries, lowercase=False):

    rouge_types = ['rouge-1', 'rouge-2', 'rouge-l']
    results = dict((rouge_type, collections.defaultdict(list))
                   for rouge_type in rouge_types)

    for ref, pred in zip(ref_summaries, pred_summaries):

        if lowercase:
            pred = pred.lower()
            ref = ref.lower()

        r1 = ROUGE_N(ref, pred, n=1)
        r2 = ROUGE_N(ref, pred, n=2)
        rl = ROUGE_L(ref, pred)

        for (rouge_type, scores) in zip(rouge_types, [r1, r2, rl]):
            results[rouge_type]['p'].append(scores.precision)
            results[rouge_type]['r'].append(scores.recall)
            results[rouge_type]['f'].append(scores.fscore)

    mean_results = {}
    for rouge_type in  rouge_types:
        precs = results[rouge_type]['p']
        recalls = results[rouge_type]['r']
        fscores = results[rouge_type]['f']
        mean_results[rouge_type] = {
            'p': round(np.mean(precs), 3),
            'r': round(np.mean(recalls), 3),
            'f': round(np.mean(fscores), 3)
        }

    return mean_results


def evaluate_from_path(dataset_path, pred_path, start, stop, lowercase=False):

    dataset = utils.read_jsonl(dataset_path)
    predictions = utils.read_jsonl(pred_path)

    rouge_types = ['rouge-1', 'rouge-2', 'rouge-l']
    results = dict((rouge_type, collections.defaultdict(list))
                   for rouge_type in rouge_types)

    for i, cluster in enumerate(dataset):
        if start > -1 and i < start:
            continue
        if stop > -1 and i >= stop:
            break

        prediction = next(predictions)
        assert prediction['cluster_id'] == cluster['id']

        hyp = prediction['summary']
        ref = cluster['summary']

        if lowercase:
            hyp = hyp.lower()
            ref = ref.lower()

        r1 = ROUGE_N(ref, hyp, n=1)
        r2 = ROUGE_N(ref, hyp, n=2)
        rl = ROUGE_L(ref, hyp)

        for (rouge_type, scores) in zip(rouge_types, [r1, r2, rl]):
            results[rouge_type]['p'].append(scores.precision)
            results[rouge_type]['r'].append(scores.recall)
            results[rouge_type]['f'].append(scores.fscore)

        if i % 100 == 0:
            print(i)
            # print_mean(results, rouge_types)

    print('Final Average:')
    print_mean(results, rouge_types)
    return results


def main(args):
    results = evaluate(args.dataset, args.preds, args.start, args.stop,
                       args.lowercase)
    utils.write_json(results, args.o)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset')
    parser.add_argument('--preds')
    parser.add_argument('--o')
    parser.add_argument('--start', type=int, default=-1)
    parser.add_argument('--stop', type=int, default=-1)
    parser.add_argument('--lowercase', action='store_true')
    main(parser.parse_args())
