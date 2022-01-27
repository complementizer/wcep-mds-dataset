import string
from nltk.corpus import stopwords

STOP_WORDS = set(stopwords.words('english'))
STOP_WORDS |= set(string.punctuation)


class Article:
    def __init__(self, title, sents):
        self.title = title
        self.sents = sents

    def words(self):
        if self.title is None:
            return [w for s in self.sents for w in s.words]
        else:
            return [w for s in [self.title] + self.sents for w in s.words]


class Sentence:
    def __init__(self, text, words, position, is_title=False):
        self.text = text
        self.words = words
        self.position = position
        self.content_words = [w for w in words if w not in STOP_WORDS]
        self.is_title = is_title

    def __len__(self):
        return len(self.words)
