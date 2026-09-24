# meme_miner_with_comments.py
# MODIFY -- this is pasted from Chat
import praw
import json
import csv
import time
from urllib.parse import urlparse
import sys
from dotenv import load_dotenv

load_dotenv()
praw_id=os.getenv("praw_id")
praw_secret=os.getenv("praw_secret")

# ----- CONFIG -----
reddit = praw.Reddit(
    client_id = praw_id,
    client_secret = praw_secret,
    user_agent = "PRAW data mining by u/resteventr0"
)

SUBREDDITS = ["dankmemes", "memes", "WholesomeMemes"]
POST_LIMIT = 10                 # posts per subreddit to examine
COMMENT_TOP_K = 10              # how many comments per post to store
COMMENT_EXPAND_LIMIT = 3        # replace_more limit (0 => expand all; 3 is a safer default)
SKIP_NSFW = True

NDJSON_OUT = "memes.ndjson"     # each line is one JSON object (post + nested comments)
COMMENTS_CSV = "comments.csv"   # one row per comment (ready for embeddings)
SLEEP_BETWEEN_POSTS = 0.5       # be polite

# create/ensure comment CSV header exists
try:
    with open(COMMENTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if f.tell() == 0:   # file empty -> write header
            writer.writerow(["post_id","subreddit","comment_id","parent_id","author","score","created_utc","body"])
except Exception as e:
    print("Failed to prepare comments CSV:", e)
    sys.exit(1)

# ---- helpers ----
def is_image_like_url(url: str) -> bool:
    if not url:
        return False
    lower = url.lower().split("?")[0]
    return any(lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".gifv", ".mp4", ".webm"])

def normalize_url(url: str) -> str:
    # Basic normalize for imgur/gifv -> not exhaustive, but handy
    if not url:
        return url
    parsed = urlparse(url)
    if "imgur.com" in parsed.netloc:
        # skip albums (/a/ or /gallery/) in this simple script
        if parsed.path.startswith("/a/") or parsed.path.startswith("/gallery/"):
            return None
        if not parsed.path.split('.')[-1]:  # no extension
            return "https://i.imgur.com" + parsed.path + ".jpg"
    if url.endswith(".gifv"):
        return url[:-5] + ".mp4"
    return url

def extract_comments(post, top_k=10, by_score=True, expand_limit=3):
    """
    Returns a list of comment dicts sorted by score or chronological.
    Each dict: comment_id, parent_id, author, body, score, created_utc
    """
    comments_out = []
    try:
        # expand some "MoreComments" placeholders (0=all; use small number to be faster)
        post.comments.replace_more(limit=expand_limit)
    except Exception as e:
        print("  warning: replace_more failed:", e)

    all_comments = post.comments.list()  # flat list
    for c in all_comments:
        # skip deleted/removed or objects that don't have body
        body = getattr(c, "body", None)
        if not body:
            continue
        body = body.strip()
        if not body or body in ("[deleted]", "[removed]"):
            continue
        comments_out.append({
            #"comment_id": getattr(c, "id", None),
            #"parent_id": getattr(c, "parent_id", None),
            #"author": str(getattr(c, "author", None)),
            "body": body,
            "score": int(getattr(c, "score", 0) or 0),
            #"created_utc": int(getattr(c, "created_utc", 0) or 0)
        })

    if not comments_out:
        return []

    if by_score:
        comments_out.sort(key=lambda x: x["score"], reverse=True)
    else:
        comments_out.sort(key=lambda x: x["created_utc"])

    return comments_out[:top_k]

def write_ndjson(obj, path=NDJSON_OUT):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def append_comments_csv(post_id, subreddit_name, comments_list, path=COMMENTS_CSV):
    if not comments_list:
        return
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for c in comments_list:
            writer.writerow([
                post_id,
                subreddit_name,
                c.get("comment_id",""),
                c.get("parent_id",""),
                c.get("author",""),
                c.get("score",0),
                c.get("created_utc",0),
                c.get("body","").replace("\n", " ").strip()
            ])

# ---- main loop ----
for sub_name in SUBREDDITS:
    sub_name = sub_name.strip()
    print("Mining", sub_name)
    try:
        subreddit = reddit.subreddit(sub_name)
    except Exception as e:
        print("  failed to access subreddit", sub_name, e)
        continue

    try:
        for post in subreddit.hot(limit=POST_LIMIT):
            try:
                if SKIP_NSFW and getattr(post, "over_18", False):
                    print("  skipping NSFW post", post.id)
                    continue

                # quick check: does post look like a media candidate?
                # we try a few heuristics: is_gallery, is_video, post_hint, or url file extension
                media_candidates = []
                if getattr(post, "is_gallery", False):
                    # keep the top-level post (gallery handling could be added later)
                    media_candidates.append(post.url)
                elif getattr(post, "is_video", False):
                    media_candidates.append(post.url)
                else:
                    # use post_hint when available
                    ph = getattr(post, "post_hint", "") or ""
                    if ph in ("image", "hosted:video", "rich:video"):
                        media_candidates.append(post.url)
                    else:
                        # fallback: check if url looks image-like or imgur/gfycat/gifv etc.
                        nurl = normalize_url(post.url)
                        if nurl and is_image_like_url(nurl):
                            media_candidates.append(nurl)

                if not media_candidates:
                    # not a likely meme image/gif/video — skip
                    continue

                # extract comments (top K by score)
                comments = extract_comments(post, top_k=COMMENT_TOP_K, by_score=True, expand_limit=COMMENT_EXPAND_LIMIT)

                # create output record: nested comments included for context
                record = {
                    "subreddit": sub_name,
                    "title": post.title,
                    "url": post.url,
                    "score": int(getattr(post, "score", 0) or 0),
                    "comments": comments

                    #"post_id": post.id,
                    #"author": str(getattr(post, "author", None)),
                    #"created_utc": int(getattr(post, "created_utc", 0) or 0),
                    #"media_candidates": media_candidates,
                    #"is_gallery": getattr(post, "is_gallery", False),
                    #"is_video": getattr(post, "is_video", False),
                    #"num_comments": int(getattr(post, "num_comments", 0) or 0),
                }

                # write incrementally
                write_ndjson(record)
                append_comments_csv(post.id, sub_name, comments)
                print(f"  saved post {post.id} with {len(comments)} comments")

                time.sleep(SLEEP_BETWEEN_POSTS)

            except Exception as e_post:
                print("  error processing post:", getattr(post, "id", "unknown"), e_post)

    except Exception as e_sub:
        print("  error iterating subreddit", sub_name, e_sub)

print("Done.")
