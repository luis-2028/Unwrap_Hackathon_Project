# Contextual Meme Retrieval Bot

Built at the Unwrap Hackathon (Oct 2025) as a team project. This repo contains
my copy of our submission; credit to my teammates Steven, Jacob, and Paul for their
work on and collaboration in this project.

## What it does

A Discord bot that watches ongoing conversation and decides, on its own, when
to drop in a relevant meme — matched semantically to what's actually being
talked about, not just triggered on a keyword or every message.

## How it works

1. **Data collection** (`reddit_scraper.py`, `memefilter.py`) — Scrapes meme
   subreddits via PRAW, pulling post titles and top comments. Filters out
   low-engagement or low-context posts by score and text length.
2. **Embedding & indexing** (`json_to_db.py`) — Embeds the filtered text with
   OpenAI's `text-embedding-3-small` and upserts the vectors into a Pinecone
   index, while storing the source meme URLs in Firebase Firestore.
3. **Retrieval** (`meme_generator.py`) — Given a query (recent conversation
   text), embeds it the same way and runs a Pinecone similarity search to
   find the closest-matching meme, then looks up its URL in Firestore.
4. **Bot logic** (`botmain.py`, `reply_tools.py`) — A Discord bot that tracks
   recent messages and uses GPT-5 with function calling to autonomously
   decide whether a meme fits the current conversation before fetching one,
   rather than firing on every message.

## Stack

Python, discord.py, OpenAI API (embeddings + GPT-5 function calling),
Pinecone (vector search), Firebase Firestore, PRAW (Reddit API)

## Setup

Requires a `.env` file with API keys for OpenAI, Pinecone, Reddit (PRAW), and
a Firebase service account JSON — none of which are included in this repo.
