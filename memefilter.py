import ndjson
import json

# remove site urls without .*
# remove not enough text comments
# remove low score

SCORE_THRESH = 150
CHAR_THRESH = 250

# paulsmemes
# paulscomedyheavenmemes
# paulsfunnymemes

IN_FILE = "paulsfunnymemes.ndjson"
OUT_FILE = "test.ndjson"


def write_ndjson(obj, path=OUT_FILE):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


with open(IN_FILE, "r") as f:
    in_data = ndjson.load(f)
    # dict_keys(['subreddit', 'title', 'url', 'score', 'comments'])
    for row in in_data:

        if row['score'] < SCORE_THRESH or \
            '.' not in row['url'].split('/')[-1]:
            continue
        text = ""
        text += row['title'] + "\n"
        text += "\n".join(comment['body'] for comment in row['comments'])
        if len(text) < CHAR_THRESH:
            continue
        
        record = {
            "url" : row['url'],
            "text" : text,
        }

        write_ndjson(record)

print("Done")
        
        





