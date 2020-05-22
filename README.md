## WCEP Dataset
### Overview
The WCEP dataset for multi-document summarization (MDS)  consists of short, human-written summaries about news events, obtained from the [Wikipedia Current Events Portal](https://en.wikipedia.org/wiki/Portal:Current_events "Wikipedia Current Events Portal") (WCEP), each paired with a cluster of news articles associated with an event. These articles consist of sources cited by editors on WCEP, and are extended with articles automatically obtained from the [Common Crawl News dataset](https://commoncrawl.org/2016/10/news-dataset-available/ "CommonCrawl News dataset"). Check out our ACL 2020 paper [A Large-Scale Multi-Document Summarization Dataset from the Wikipedia Current Events Portal](https://arxiv.org/abs/2005.10070) for more info about the dataset and experiments.
### Dataset Generation
We currently do not provide the entire dataset for download. Instead, we share the summaries from WCEP and scripts that obtain the associated news articles. Make sure to set `--jobs` to your avaible number of CPUs to speed things up. Both scripts can be interrupted and resumed by just repeating the same command. To restart from scratch, add `--override`.

At first, download the inital [dataset without articles](https://drive.google.com/file/d/1LGYFKGzCgvdllwIQHDF5qSxtan1Y0Re9/view?usp=sharing "dataset without articles") and place it in `/data`.
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
Finally, we need to group articles and summaries belonging together, and split the dataset into separate train/validation/test files.
```bash
python combine_and_split.py \
    --dataset data/initial_dataset.jsonl \
    --cc-articles data/cc_storage/cc_articles.jsonl \
    --wcep-articles data/wcep_articles.jsonl \
    --o data/wcep_dataset
```

### Loading the dataset
We store the dataset in a jsonl format, where each line corresponds to a news event, associated with a summary and a cluster of news articles, and some metadata, such as date and category. The summarization task is to reconstruct the summary from the news articles.

```python
import json

def read_jsonl(path):
    with open(path) as f:
        for line in f:
            yield json.loads(line)

val_data = list(read_jsonl('data/wcep_dataset/val.jsonl'))
c = val_data[404]
summary = c['summary'] # human-written summary
articles = c['articles'] # cluster of articles
```
