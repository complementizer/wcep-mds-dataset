import re
from nltk import sent_tokenize


class SentenceSplitter:
    """
    NLTK sent_tokenize + some fixes for common errors in news articles.
    """
    def unglue(self, x):
        g = x.group(0)
        fixed = '{} {}'.format(g[0], g[1])
        return fixed

    def fix_glued_sents(self, text):
        return re.sub(r'\.[A-Z]', self.unglue, text)

    def fix_line_broken_sents(self, sents):
        new_sents = []
        for s in sents:
            new_sents += [s_.strip() for s_ in s.split('\n')]
        return new_sents

    def split_sents(self, text):
        text = self.fix_glued_sents(text)
        sents = sent_tokenize(text)
        sents = self.fix_line_broken_sents(sents)
        sents = [s for s in sents if s != '']
        return sents
