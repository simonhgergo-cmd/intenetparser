# intenetparser

Collects public posts from free sources, finds what people **struggle with**, **wish existed** and
**love**, and breaks it down by audience segment. The goal is to find problems worth building
products for.

- Free sources only. No paid APIs and no required dependencies (Python 3.11+ standard library).
- Keyword-based analysis that runs offline, plus exports you can paste into Claude or run through a
  local LLM for better quality.
- One self-contained HTML report.

## Getting started (no typing needed)

**1. Install Python** (one time). Download it from https://www.python.org/downloads/ and run the
installer. **On Windows, tick "Add python.exe to PATH"** at the bottom of the first installer
screen before clicking Install Now.

**2. Download this project.** On https://github.com/simonhgergo-cmd/intenetparser click the green
**Code** button, then **Download ZIP**. Unzip it somewhere you'll find again, e.g. Documents.

**3. Double-click the start file** in the unzipped folder:

| Your computer | File to double-click |
|---|---|
| Windows | `Start (Windows).bat`. If a blue "Windows protected your PC" box appears: **More info** → **Run anyway**. |
| Mac | `Start (Mac).command`. If macOS says it can't verify the developer: right-click the file → **Open** → **Open**. |
| Linux | `start-linux.sh` (or run `./start-linux.sh` in a terminal) |

A control panel opens in your browser (in Hungarian). It runs only on your computer and only you
can reach it:

- **Áttekintés** (overview): start a collection (**Gyűjtés most**), keep collecting on a schedule
  (**Folyamatos gyűjtés**), watch progress, see the time estimate and open the report.
- **Beállítások** (settings): tick which groups of people and which sources to cover, pick the
  Reddit mode, schedule and storage limit.
- **Claude-hoz** (for Claude): copy the files to paste into Claude with one click.

A small black window also opens (minimised on Windows). That's the program itself: keep it open
while you use the panel, because closing it stops everything. Your computer must stay on and awake
while it collects.

If you prefer a text menu in the terminal, run `python3 -m iparse menu`.

### Reddit: nothing to set up

Reddit is most of the data. By default it's read from
[Arctic Shift](https://arctic-shift.photon-reddit.com), a free public archive of Reddit that
researchers and moderators use. No account, key or approval is needed, and it returns 100 posts or
comments per request.

- It's run by a third party, not Reddit. If it can't be reached, the tool automatically reads Reddit
  directly instead. That still works without an account, but Reddit then allows only about 10
  requests a minute, so a full run takes hours.
- Scores (upvotes) are captured soon after posting, so they're often lower than what Reddit shows
  later. That only affects how themes are weighted.
- Reddit's own API now needs Reddit's approval to create an app (Responsible Builder Policy). If
  you get approved, enter the client ID and secret in the setup wizard; the tool then reads Reddit
  directly at 100 requests a minute.

## Disk space

Measured: **about 1 KB per collected post or comment**, including the analysis.

| | Approximate size |
|---|---|
| First run (all groups) | ~100 MB |
| Each later run (mostly new comments) | ~30–40 MB |
| Collecting every 12 h | ~70 MB/day, ~2 GB/month |
| Upper limit with the default `keep_days = 90` | ~6–7 GB |
| Report and Claude files | a few MB, overwritten each run |

These are estimates from the expected new posts per run. The control panel shows the real size.
To use less space, lower `keep_days` in `config.toml` (posts older than that are deleted), cover
fewer groups, or collect less often. Everything is stored in the `data` folder; deleting it
starts over.

## Command line (optional)

Everything in the control panel is also available as commands, for scripting or servers:

```bash
python3 -m iparse init           # or: pip install -e . and then use `iparse`
python3 -m iparse plan
python3 -m iparse run --once
```

## Speed and volume

With the default config, which covers all ~70 non-sensitive groups in the catalog, one run is
roughly **1,100 requests, ~80,000 posts and comments, ~15–20 minutes**. Reddit through the
archive takes ~10 minutes; App Store reviews are now the slowest part.

`iparse plan` (or the estimate on the control panel) prints this for your own config. These are estimates from request
counts and rate limits; real runs vary with errors and retries.

How it stays fast:

- All sources run in parallel, so total time is the slowest source, not the sum.
- Each site gets its own request rate, matched to its published limits (`iparse/http.py`).
- Reddit posts and comments come 100 per request (a subreddit's newest ones).
- Posts already in the database don't get their comments fetched again.
- Analysis uses every CPU core (about 10,000 posts/s on 4 cores) and only touches new posts.

## Coverage: the catalog

`iparse catalog` lists the built-in groups, each mapped to its subreddits, Stack Exchange sites,
Mastodon hashtags and App Store search terms:

- **audience** (who people are): parents, teens, college students, retirees, caregivers,
  immigrants, low income, nurses, teachers, trades, gig drivers, small business owners, job
  seekers, renters, pet owners and more
- **interest** (what they're into): fitness, cooking, gaming, cars, DIY, gardening, fashion and
  beauty, investing, sustainability and more
- **region**: US, UK, Canada, Australia, India, Ireland, New Zealand, Philippines, Nigeria,
  South Africa, Singapore, Germany (English-language communities)

Choose groups in `[catalog]`: `groups = ["*"]` for all, `["audience"]`, `["parents", "teachers"]`
or `["*", "-gaming"]`. Health, disability and LGBTQ+ communities are included only with
`include_sensitive = true`; they're labelled by community, never by inferring anything about an
individual.

To add a group the catalog lacks, run `iparse discover "keyword"`. It lists matching subreddits
by size and prints the lines to paste into your config.

## Sources

| Source | Status | What you need |
|---|---|---|
| Reddit | on | Nothing: read from the free Arctic Shift archive, or directly from Reddit if the archive is down or you have an approved app |
| Hacker News | on | Nothing |
| Bluesky (free stand-in for X) | on | Search may require a free account + app password |
| Mastodon | on | Nothing |
| Stack Exchange (parenting, money, cooking, workplace, ...) | on | Nothing. A free key raises the daily limit. |
| Apple App Store reviews | on | Nothing. 1–2 star reviews of popular apps = unmet needs. |
| YouTube comments | off | Free API key (10,000 units/day, no billing) |
| TikTok | off, experimental | `pip install -e '.[tiktok]' && playwright install chromium` |
| Instagram, X, anything else | via import | Put CSV/JSON/TXT files in a folder and point `[sources.import]` at it |

**What's not covered, and why:** X has no free API, and Instagram shows almost nothing to
logged-out visitors. The TikTok collector only reads public pages while logged out: it never logs
in, likes, follows or posts, and doesn't try to hide that it's automated. TikTok often shows
captchas or empty pages to it, so expect patchy results. Automated access breaks TikTok's terms;
whether to turn it on is up to you. Bluesky and Mastodon cover the same kind of short public posts
as X. For Instagram, copy comments or posts you care about into a file and import them.

## Commands

```
iparse init                      create config.toml
iparse plan                      estimate requests, posts and time per source
iparse catalog                   list built-in groups of people
iparse discover KEYWORD          find subreddits to add
iparse collect [--source NAME]   fetch posts (repeat --source to pick several)
iparse analyze [--all]           keyword analysis of new posts (--all re-analyses everything)
iparse report                    write reports/report.html
iparse export csv|jsonl          everything, for spreadsheets / pandas
iparse export llm                prompt packs for Claude or a local model (see below)
iparse llm --model NAME          run the packs through a local OpenAI-compatible model
iparse run [--every 12h] [--once] collect -> analyse -> report -> export, forever
iparse app                       browser control panel (what the start files open)
iparse menu / iparse setup       text menu / setup wizard in the terminal
iparse stats                     what's in the database
```

Collecting again doesn't create duplicates; it refreshes scores and comment counts.

### Running it 24/7

The control panel's "Folyamatos gyűjtés" button does this. From a terminal, `iparse run` loops on its own; to keep it alive
after you log out:

```bash
nohup iparse run --every 12h > iparse.log 2>&1 &
```

Or use cron instead (`crontab -e`):

```
0 */12 * * * cd /path/to/intenetparser && .venv/bin/iparse run --once >> iparse.log 2>&1
```

## Reading the report

Pick a segment and you get four lists:

- **Problems**: complaints and struggles, ranked by how many posts mention them, weighted by
  upvotes/likes and how negative the post is.
- **Wishes and requests**: "I wish there was...", "is there an app that...", "I'd pay for...",
  "someone should build...". These are the most direct product leads.
- **What makes people happy**: things people love, recommend or call a game changer. This tells
  you what "good" looks like for that group.
- **Most talked about**: common phrases. For a segment, ranked by how much *more* that group talks
  about it than everyone else.

Click a theme to see the quotes behind it, with links to the originals.

### Segments, honestly

Platforms don't say who posted something, so "every demographic" can only be approximated:

- `audience:*`, `interest:*` and `region:*` come from where a post was made (r/Parenting →
  parents, r/AusFinance → Australia), using the catalog. That describes the community, not the
  person. Add your own mappings under `[segments.communities]`.
- `age:*`, `gender:*`, `role:*`, `life:*`, `housing:*` are only set when authors say it about
  themselves ("I'm a nurse", "34F", "my toddler", "my landlord").
- `platform:*` is the source.

Nothing sensitive (health, ethnicity, religion, politics, sexuality) is inferred. Self-reported
segments are small, because most posts don't mention who wrote them.

## Better analysis with an LLM

The keyword analyser is fast and transparent, but it misses sarcasm, context and anything phrased
in an unusual way. It's best for finding leads. `iparse export llm` (also run by `iparse run`)
writes `exports/llm/`:

- `pack_001.md`, `pack_002.md`, ...: instructions plus a batch of posts that had a problem, wish
  or joy. Paste one into Claude, or any chat model, and you get structured JSON back per post:
  problems with severity, wishes, who the author is and a product idea.
- `summary.md`: all themes per segment with example quotes, plus a prompt asking for merged
  problems and ranked product ideas with evidence. This is the one to paste first.

Use `--max-chars` to fit your model's context (default 60,000 characters, roughly 15k tokens).

Local model, nothing leaves your machine (for example with [Ollama](https://ollama.com)):

```bash
ollama pull llama3.1
iparse llm --model llama3.1                                   # Ollama default URL
iparse llm --model qwen2.5 --url http://localhost:1234/v1     # LM Studio
```

Responses go to `exports/llm/responses/`.

## Tuning

- **Communities and queries:** `config.toml`. Pick subreddits, hashtags and Stack Exchange sites
  that match the groups you care about.
- **Patterns:** `iparse/analysis/lexicon.py` holds every regex for problems, wishes and joys, plus
  the sentiment word list. Add phrasings you see in your data, then run `iparse analyze --all`.
- **Thresholds:** `[analysis]`. Lower `min_mentions` to see rarer themes.
- **Volume:** `posts_per_listing`, `comments_per_sub` and `archive_days` under
  `[sources.reddit]`. Check the effect with `iparse plan`.

## Data and privacy

- Author names are stored only as salted hashes (set your own `author_salt`).
- Everything stays local: `data/iparse.db` (SQLite), `reports/`, `exports/`.
- Collect at a polite pace and respect each platform's terms; you're responsible for how you use
  the data.

## Development

```bash
python3 -m unittest discover -s tests -t .
```

Layout: `iparse/sources/` (one file per platform), `iparse/catalog.py` (groups and their
communities), `iparse/analysis/` (analyser, segments, aggregation), `iparse/report.py`, `iparse/export.py`, `iparse/pipeline.py`, `iparse/cli.py`.
