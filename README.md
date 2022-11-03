## WCEP Dataset
### Overview
The WCEP dataset for multi-document summarization (MDS)  consists of short, human-written summaries about news events, obtained from the [Wikipedia Current Events Portal](https://en.wikipedia.org/wiki/Portal:Current_events "Wikipedia Current Events Portal") (WCEP), each paired with a cluster of news articles associated with an event. These articles consist of sources cited by editors on WCEP, and are extended with articles automatically obtained from the [Common Crawl News dataset](https://commoncrawl.org/2016/10/news-dataset-available/ "CommonCrawl News dataset"). For more information about the dataset and experiments, check out our ACL 2020 paper: *A Large-Scale Multi-Document Summarization Dataset from the Wikipedia Current Events Portal.* ([Paper](https://www.aclweb.org/anthology/2020.acl-main.120/),  [Slides](acl20-slides.pdf))

### Colab Notebook


[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/complementizer/wcep-mds-dataset/blob/master/wcep_getting_started.ipynb)

You can use this notebook to
* download & inspect the dataset
* run extractive baselines & oracles
* evaluate summaries

Otherwise, check out the instructions below.

### Download Dataset

Update 6.10.20: [an extracted version of the dataset can be downloaded here](https://drive.google.com/drive/folders/1T5wDxu4ajFwEq77dG88oE95e8ppREamg?usp=sharing)

### Loading the Dataset
We store the dataset in a gzipped jsonl format, where each line corresponds to a news event, associated with a summary and a cluster of news articles, and some metadata, such as date and category. The summarization task is to generate the summary from the news articles.

```python
import json, gzip

def read_jsonl_gz(path):
    with gzip.open(path) as f:
        for l in f:
            yield json.loads(l)

val_data = list(read_jsonl_gz('<WCEP path>/val.jsonl.gz'))
c = val_data[404]
summary = c['summary'] # human-written summary
articles = c['articles'] # cluster of articles
```

### Extractive Baselines and Evaluation

We also provide code to run several extractive baselines and evaluate
generated summaries. Note that we just use the ROUGE wrapper of the [newsroom library](https://github.com/lil-lab/newsroom) to compute ROUGE scores.

Install dependencies:

`pip install -r experiments/requirements.txt`

`cd` to [experiments](experiments) to run this snippet:

```python
from utils import read_jsonl_gz
from baselines import TextRankSummarizer
from evaluate import evaluate
from pprint import pprint

val_data = list(read_jsonl_gz('<INSERT WCEP PATH>/val.jsonl.gz'))

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
```

### Dataset Generation

**Note:** This is currently not required as the dataset is available for download.

We currently do not provide the entire dataset for download. Instead, we share the summaries from WCEP and scripts that obtain the associated news articles. Make sure to set `--jobs` to your avaible number of CPUs to speed things up. Both scripts can be interrupted and resumed by just repeating the same command. To restart from scratch, add `--override`.

Install dependencies:
```bash
pip install dataset_generation/requirements.txt
```

At first, download the inital [dataset without articles](https://drive.google.com/file/d/1LGYFKGzCgvdllwIQHDF5qSxtan1Y0Re9/view?usp=sharing "dataset without articles"), place it in `/data` (unzipped).
##### 1) Extracting articles from WCEP
This script extracts news articles from various news sources cited on WCEP using [newspaper3k](https://github.com/codelucas/newspaper "newspaper3k") from the [Internet Archive Wayback Machine](https://archive.org/). We previously requested snapshots of all source articles that were not archived yet.

```bash
python extract_wcep_articles.py \
    --i data/initial_dataset.jsonl \
    --o data/wcep_articles.jsonl \
    --batchsize 200 \
    --jobs 16 \
    --repeat-failed
```
If any downloads fail due to timeouts, simply repeat the same command. It will only attempt to extract the missing articles.
##### 2) Extracting articles from Common Crawl
This script extracts articles from Common Crawl News, which is divided into ~6000 files of 1GB size each. These are downloaded and searched one at a time. The relevant articles are extracted from HTML in parallel using newspaper3k.
```bash
python extract_cc_articles.py \
    --storage data/cc_storage \
    --dataset data/initial_dataset.jsonl \
    --batchsize 200 \
    --max-cluster-size 100 \
    --jobs 16
```

This process takes a long time (few days!). We are working on speeding it up.
`--max-cluster-size 100` already reduces the time: only up to 100 articles of each cluster in the dataset are extracted. This corresponds to the dataset version used in the experiments in our paper ("WCEP-100").
##### 3) Combine and split
Finally, we need to group articles and summaries belonging together, and split the dataset into separate train/validation/test files. If `--max-cluster-size` was used in the previous step, use that here accordingly.
```bash
python combine_and_split.py \
    --dataset data/initial_dataset.jsonl \
    --cc-articles data/cc_storage/cc_articles.jsonl \
    --wcep-articles data/wcep_articles.jsonl \
    --max-cluster-size 100 \
    --o data/wcep_dataset    
```

### Citation

If you find this dataset useful, please cite:
```
@inproceedings{gholipour-ghalandari-etal-2020-large,
    title = "A Large-Scale Multi-Document Summarization Dataset from the {W}ikipedia Current Events Portal",
    author = "Gholipour Ghalandari, Demian  and
      Hokamp, Chris  and
      Pham, Nghia The  and
      Glover, John  and
      Ifrim, Georgiana",
    booktitle = "Proceedings of the 58th Annual Meeting of the Association for Computational Linguistics",
    month = jul,
    year = "2020",
    address = "Online",
    publisher = "Association for Computational Linguistics",
    url = "https://www.aclweb.org/anthology/2020.acl-main.120",
    pages = "1302--1308",
}
```
