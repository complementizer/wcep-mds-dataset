import utils
from nltk import word_tokenize, bigrams
from sent_splitter import SentenceSplitter
from data import Sentence, Article


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
