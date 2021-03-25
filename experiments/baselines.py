import utils
import random
import collections
import numpy as np
import networkx as nx
import warnings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import MiniBatchKMeans
from summarizer import Summarizer


warnings.filterwarnings('ignore', category=RuntimeWarning)
random.seed(24)


class RandomBaseline(Summarizer):

    def summarize(self,
                  articles,
                  max_len=40,
                  len_type='words',
                  in_titles=False,
                  out_titles=False,
                  min_sent_tokens=7,
                  max_sent_tokens=40):

        articles = self._preprocess(articles)
        sents = [s for a in articles for s in a.sents]
        if in_titles == False or out_titles == False:
            sents = [s for s in sents if not s.is_title]
        sents = self._deduplicate(sents)
        sent_lens = [self._sent_len(s, len_type) for s in sents]

        current_len = 0
        remaining = list(range(len(sents)))
        random.shuffle(remaining)

        selected = []
        for i in remaining:
            new_len = current_len + sent_lens[i]
            if new_len <= max_len:
                if not (min_sent_tokens <= len(
                        sents[i].words) <= max_sent_tokens):
                    continue
                selected.append(i)
                current_len = new_len
            if current_len >= max_len:
                break

        summary_sents = [sents[i].text for i in selected]
        return ' '.join(summary_sents)


class RandomLead(Summarizer):

    def summarize(self,
                  articles,
                  max_len=40,
                  len_type='words',
                  in_titles=False,
                  out_titles=False,
                  min_sent_tokens=7,
                  max_sent_tokens=40):

        article_idxs = list(range(len(articles)))
        random.shuffle(article_idxs)
        summary = ''
        for i in article_idxs:
            a = articles[i]
            a = self._preprocess([a])[0]
            sents = a.sents
            if in_titles == False or out_titles == False:
                sents = [s for s in sents if not s.is_title]
            current_len = 0
            selected_sents = []
            for s in sents:
                l = self._sent_len(s, len_type)
                new_len = current_len + l
                if new_len <= max_len:
                    if not (min_sent_tokens <= len(s.words) <= max_sent_tokens):
                        continue
                    selected_sents.append(s.text)
                    current_len = new_len
                if new_len > max_len:
                    break
            if len(selected_sents) >= 1:
                summary = ' '.join(selected_sents)
                break
        return summary


class TextRankSummarizer(Summarizer):
    def __init__(self, max_redundancy=0.5):
        self.max_redundancy = max_redundancy

    def _compute_page_rank(self, S):
        nodes = list(range(S.shape[0]))
        graph = nx.from_numpy_matrix(S)
        pagerank = nx.pagerank(graph, weight='weight')
        scores = [pagerank[i] for i in nodes]
        return scores

    def summarize(self,
                  articles,
                  max_len=40,
                  len_type='words',
                  in_titles=False,
                  out_titles=False,
                  min_sent_tokens=7,
                  max_sent_tokens=40):

        articles = self._preprocess(articles)
        sents = [s for a in articles for s in a.sents]
        if in_titles == False:
            sents = [s for s in sents if not s.is_title]
        sents = self._deduplicate(sents)
        sent_lens = [self._sent_len(s, len_type) for s in sents]
        raw_sents = [s.text for s in sents]

        vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
        X = vectorizer.fit_transform(raw_sents)
        S = cosine_similarity(X)

        scores = self._compute_page_rank(S)
        scored = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        if not out_titles:
            scored = [(i, score) for (i, score) in scored
                      if not sents[i].is_title]

        current_len = 0
        selected = []
        for i, _ in scored:
            new_len = current_len + sent_lens[i]
            if new_len <= max_len:
                if self._is_redundant(
                        sents, selected, i, self.max_redundancy):
                    continue
                if not (min_sent_tokens <= len(
                        sents[i].words) <= max_sent_tokens):
                    continue

                selected.append(i)
                current_len = new_len

        summary_sents = [sents[i].text for i in selected]
        return ' '.join(summary_sents)


class CentroidSummarizer(Summarizer):
    def __init__(self, max_redundancy=0.5):
        self.max_redundancy = max_redundancy

    def summarize(self,
                  articles,
                  max_len=40,
                  len_type='words',
                  in_titles=False,
                  out_titles=False,
                  min_sent_tokens=7,
                  max_sent_tokens=40):

        articles = self._preprocess(articles)
        sents = [s for a in articles for s in a.sents]
        if in_titles == False:
            sents = [s for s in sents if not s.is_title]
        sents = self._deduplicate(sents)
        sent_lens = [self._sent_len(s, len_type) for s in sents]
        raw_sents = [s.text for s in sents]

        vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
        try:
            X = vectorizer.fit_transform(raw_sents)
        except:
            return ''

        centroid = X.mean(0)
        scores = cosine_similarity(X, centroid)
        scored = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        if not out_titles:
            scored = [(i, score) for (i, score) in scored
                      if not sents[i].is_title]

        current_len = 0
        selected = []
        for i, _ in scored:
            new_len = current_len + sent_lens[i]
            if new_len <= max_len:
                if self._is_redundant(
                    sents, selected, i, self.max_redundancy):
                    continue
                if not (min_sent_tokens <= len(
                        sents[i].words) <= max_sent_tokens):
                    continue

                selected.append(i)
                current_len = new_len

        summary_sents = [sents[i].text for i in selected]
        return ' '.join(summary_sents)


class SubmodularSummarizer(Summarizer):
    """
    Selects a combination of sentences as a summary by greedily optimizing
    a submodular function, in this case two functions representing
    coverage and diversity of the sentence combination.
    """
    def __init__(self, a=5, div_weight=6, cluster_factor=0.2):
        self.a = a
        self.div_weight = div_weight
        self.cluster_factor = cluster_factor

    def cluster_sentences(self, X):
        n = X.shape[0]
        n_clusters = round(self.cluster_factor * n)
        if n_clusters <= 1 or n <= 2:
            return dict((i, 1) for i in range(n))
        clusterer = MiniBatchKMeans(
            n_clusters=n_clusters,
            init_size=3 * n_clusters
        )
        labels = clusterer.fit_predict(X)
        i_to_label = dict((i, l) for i, l in enumerate(labels))
        return i_to_label

    def compute_summary_coverage(self,
                                 alpha,
                                 summary_indices,
                                 sent_coverages,
                                 pairwise_sims):
        cov = 0
        for i, i_generic_cov in enumerate(sent_coverages):
            i_summary_cov = sum([pairwise_sims[i, j] for j in summary_indices])
            i_cov = min(i_summary_cov, alpha * i_generic_cov)
            cov += i_cov
        return cov

    def compute_summary_diversity(self,
                                  summary_indices,
                                  ix_to_label,
                                  avg_sent_sims):

        cluster_to_ixs = collections.defaultdict(list)
        for i in summary_indices:
            l = ix_to_label[i]
            cluster_to_ixs[l].append(i)
        div = 0
        for l, l_indices in cluster_to_ixs.items():
            cluster_score = sum([avg_sent_sims[i] for i in l_indices])
            cluster_score = np.sqrt(cluster_score)
            div += cluster_score
        return div

    def optimize(self,
                 sents,
                 max_len,
                 len_type,
                 ix_to_label,
                 pairwise_sims,
                 sent_coverages,
                 avg_sent_sims,
                 out_titles,
                 min_sent_tokens,
                 max_sent_tokens):

        alpha = self.a / len(sents)
        sent_lens = [self._sent_len(s, len_type) for s in sents]
        current_len = 0
        remaining = set(range(len(sents)))

        for i, s in enumerate(sents):
            bad_length = not (min_sent_tokens <= len(sents[i].words)
                              <= max_sent_tokens)
            if bad_length:
                remaining.remove(i)
            elif out_titles == False and s.is_title:
                remaining.remove(i)

        selected = []
        scored_selections = []

        while current_len < max_len and len(remaining) > 0:
            scored = []
            for i in remaining:
                new_len = current_len + sent_lens[i]
                if new_len <= max_len:
                    summary_indices = selected + [i]
                    cov = self.compute_summary_coverage(
                        alpha, summary_indices, sent_coverages, pairwise_sims)
                    div = self.compute_summary_diversity(
                        summary_indices, ix_to_label, avg_sent_sims)
                    score = cov + self.div_weight * div
                    scored.append((i, score))

            if len(scored) == 0:
                break
            scored.sort(key=lambda x: x[1], reverse=True)
            best_idx, best_score = scored[0]
            scored_selections.append((selected + [best_idx], best_score))
            current_len += sent_lens[best_idx]
            selected.append(best_idx)
            remaining.remove(best_idx)

        scored_selections.sort(key=lambda x: x[1], reverse=True)
        best_selection = scored_selections[0][0]
        return best_selection

    def summarize(self,
                  articles,
                  max_len=40,
                  len_type='words',
                  in_titles=False,
                  out_titles=False,
                  min_sent_tokens=7,
                  max_sent_tokens=40):
                  
        articles = self._preprocess(articles)
        sents = [s for a in articles for s in a.sents]
        if in_titles == False:
            sents = [s for s in sents if not s.is_title]
        sents = self._deduplicate(sents)
        raw_sents = [s.text for s in sents]

        vectorizer = TfidfVectorizer(lowercase=True, stop_words='english')
        X = vectorizer.fit_transform(raw_sents)

        ix_to_label = self.cluster_sentences(X)
        pairwise_sims = cosine_similarity(X)
        sent_coverages = pairwise_sims.sum(0)
        avg_sent_sims = sent_coverages / len(sents)

        selected = self.optimize(
            sents, max_len, len_type, ix_to_label,
            pairwise_sims, sent_coverages, avg_sent_sims,
            out_titles, min_sent_tokens, max_sent_tokens
        )

        summary = [sents[i].text for i in selected]
        return ' '.join(summary)
