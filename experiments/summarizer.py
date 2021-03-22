import ray
import utils
from nltk import word_tokenize, bigrams
from sent_splitter import SentenceSplitter
from data import Sentence, Article


def summarize(summarizer, cluster, **summarize_settings):
    summary = summarizer.summarise(
        cluster['articles'], **summarize_settings
    )
    prediction = {
        'summary': summary,
        'cluster_id': cluster['id'],
    }
    return prediction


def oracle_summarize(summarizer, cluster, **summarize_settings):
    summary = summarizer.summarise(
        cluster['summary'], cluster['articles'], **summarize_settings
    )
    prediction = {
        'summary': summary,
        'cluster_id': cluster['id'],
    }
    return prediction


@ray.remote
def summarize_worker(summarizer, cluster, **summarize_settings):
    summary = summarizer.summarise(cluster['articles'], **summarize_settings)
    prediction = {
        'summary': summary,
        'cluster_id': cluster['id'],
    }
    return prediction


@ray.remote
def oracle_worker(summarizer, cluster, **summarize_settings):
    summary = summarizer.summarise(
        cluster['summary'], cluster['articles'], **summarize_settings
    )
    prediction = {
        'summary': summary,
        'cluster_id': cluster['id'],
    }
    return prediction


class Summarizer:

    def _deduplicate(self, sents):
        seen = set()
        uniq_sents = []
        for s in sents:
            if s.text not in seen:
                seen.add(s.text)
                uniq_sents.append(s)
        return uniq_sents

    def _sent_len(self, sent, len_type):
        if len_type == 'chars':
            return len(sent.text)
        elif len_type == 'words':
            return len(sent.words)
        elif len_type == 'sents':
            return 1
        else:
            raise ValueError('len_type must be in (chars|words|sents)')

    def _is_redundant(self, sents, selected, new, max_redundancy):
        new_bigrams = list(bigrams(sents[new].words))
        l = len(new_bigrams)
        for i in selected:
            old_bigrams = list(bigrams(sents[i].words))
            n_matching = len([x for x in new_bigrams if x in old_bigrams])
            if n_matching == 0:
                continue
            else:
                overlap = n_matching / l
                if overlap >= max_redundancy:
                    return True
        return False

    def _preprocess(self, articles):
        sent_splitter = SentenceSplitter()
        processed_articles = []
        for a in articles:
            body_sents = sent_splitter.split_sents(a['text'])
            processed_title = Sentence(
                text=a['title'],
                words=word_tokenize(a['title']),
                position=-1,
                is_title=True
            )
            processed_sents = []
            for position, s in enumerate(body_sents):
                processed_sent = Sentence(
                    text=s,
                    words=word_tokenize(s),
                    position=position
                )
                processed_sents.append(processed_sent)

            processed_article = Article(processed_title, processed_sents)
            processed_articles.append(processed_article)

        return processed_articles

    def _preprocess_sents(self, raw_sents):
        processed_sents = []
        for s in raw_sents:
            processed_sent = Sentence(
                text=s,
                words=word_tokenize(s),
                position=None
            )
            processed_sents.append(processed_sent)
        return processed_sents

    def summarize(self,
                  articles,
                  max_len=40,
                  len_type='words',
                  in_titles=False,
                  out_titles=False,
                  min_sent_tokens=60,
                  max_sent_tokens=7):
        raise NotImplementedError

    @staticmethod
    def summarize_clusters(summarizer,
                           clusters,
                           pred_path,
                           summarize_settings,
                           oracle=False,
                           jobs=1):
        if jobs == 1:
            if oracle:
                predictions = [
                    oracle_summarize(summarizer, c, **summarize_settings)
                    for c in clusters
                ]
            else:
                predictions = [
                    summarize(summarizer, c, **summarize_settings)
                    for c in clusters
                ]
            utils.write_jsonl(predictions, pred_path, override=False)

        else:
            if oracle:
                predictions = [
                    oracle_worker.remote(summarizer, c, **summarize_settings)
                    for c in clusters
                ]

            else:
                predictions = [
                    summarize_worker.remote(summarizer, c, **summarize_settings)
                    for c in clusters
                ]
            predictions = ray.get(predictions)
            utils.write_jsonl(predictions, pred_path, override=False)

    @staticmethod
    def summarize_dataset(summarizer,
                          dataset_path,
                          pred_path,
                          summarize_settings,
                          start=-1,
                          stop=-1,
                          batchsize=32,
                          jobs=4,
                          oracle=False):

        print('START:', start, 'STOP', stop)
        if jobs > 1:
            ray.init(num_cpus=jobs)

        dataset = utils.read_jsonl(dataset_path)
        utils.write_jsonl([], pred_path)

        batch = []
        n_done = 0
        for i, c in enumerate(dataset):
            if start > -1 and i < start:
                continue
            if stop > -1 and i >= stop:
                break

            batch.append(c)
            if len(batch) >= batchsize:
                print(f'{n_done} clusters done')
                Summarizer.summarize_clusters(
                    summarizer=summarizer,
                    summarize_settings=summarize_settings,
                    clusters=batch,
                    pred_path=pred_path,
                    oracle=oracle,
                    jobs=jobs
                )
                n_done += len(batch)
                batch = []

        Summarizer.summarize_clusters(
            summarizer=summarizer,
            summarize_settings=summarize_settings,
            clusters=batch,
            pred_path=pred_path,
            oracle=oracle,
            jobs=jobs
        )
        if jobs > 1:
            ray.shutdown()
