"""Word lists and phrase patterns for the keyword-based analyser.

Every pattern is (regex, weight, object_side). object_side says where the
thing being complained about / praised usually sits relative to the match:
"after" ("struggling with [meal planning]") or "before" ("[my landlord] is a
nightmare"). Edit freely; this is the main knob for analysis quality.
"""

# --- problems -------------------------------------------------------------
PROBLEM_PATTERNS = [
    (r"\b(?:struggl(?:e|es|ing|ed)|having (?:a )?(?:hard|tough|difficult) time|having (?:trouble|issues|problems)|problems?|issues?|trouble) (?:with|to|finding|getting|keeping)\b", 1.0, "after"),
    (r"\bcan'?t (?:seem to |ever )?(?=(?:find|figure out|afford|get|stop|keep|manage|handle|deal with|sleep|focus|decide|understand|motivate)\b)", 1.0, "after"),
    (r"\b(?:i|we) (?:really |absolutely |just |honestly )?(?:hate|despise|dread|can'?t stand)\b", 1.0, "after"),
    (r"\b(?:sick of|tired of|fed up with|annoyed (?:by|with|at)|frustrated (?:by|with|at)|sick and tired of)\b", 1.0, "after"),
    (r"\b(?:it'?s|it is|its) (?:so |really |very |super |incredibly |way too |too )?(?:hard|difficult|impossible|annoying|frustrating|exhausting|expensive|confusing|stressful) to\b", 1.0, "after"),
    (r"\bwhy (?:is|are) (?:it|there|everything) (?:so )?(?:hard|difficult|expensive|impossible) to\b", 1.0, "after"),
    (r"\bhow (?:do|can|does|should) (?:i|you|we|people|anyone) (?:even )?(?:deal with|cope with|stop|get rid of|handle|manage|afford|fix|avoid)\b", 0.8, "after"),
    (r"\b(?:need|could use) (?:some )?(?:help|advice) (?:with|on)\b", 0.8, "after"),
    (r"\banyone else (?:struggl\w+|deal\w*|ha(?:ve|ving)|hate|feel\w*|notic\w+|annoyed)(?: with| by)?\b", 0.9, "after"),
    (r"\b(?:stressed|worried|anxious|scared|afraid|terrified|overwhelmed|burn(?:ed|t) out) (?:about|of|by|with|from)\b", 0.9, "after"),
    (r"\b(?:nobody|no one) (?:tells you|talks about|warns you)(?: about)?\b", 0.7, "after"),
    (r"\b(?:is|are|was|were|has been|have been) (?:such a |a |an |so |really |very |completely |absolutely |way )?(?:complete |total |huge |real |hot )?(?:nightmare|pain|joke|scam|ripoff|rip-off|mess|disaster|frustrating|annoying|overpriced|too expensive|broken|useless|terrible|awful|horrible|unbearable|exhausting|overwhelming|unaffordable|confusing)\b", 1.0, "before"),
    (r"\b(?:doesn'?t|does not|don'?t|won'?t|never|stopped|keeps? not) work(?:s|ing|ed)?\b", 0.8, "before"),
    (r"\b(?:is|was|are) a (?:complete |total )?waste of (?:time|money)\b", 1.0, "before"),
    (r"\b(?:keeps?|kept) (?:crashing|breaking|failing|freezing|logging me out|charging me)\b", 0.9, "before"),
]

# Requests for something that does not exist yet: the strongest product signal.
WISH_PATTERNS = [
    (r"\bi (?:really |just )?wish (?:there (?:was|were|is)|i could|someone would|i had|they would|it would|i knew)\b", 1.0, "after"),
    (r"\bis there (?:a|an|any) (?:way|app|tool|product|service|website|site|thing|device|program|software) (?:to|that|for|which)\b", 1.0, "after"),
    (r"\b(?:does|do) (?:anyone|anybody) know (?:a|an|of a|of any|any) (?:way|app|tool|product|service|website)\b", 1.0, "after"),
    (r"\bsomeone (?:should|needs to|has to|pls|please) (?:make|build|invent|create|start)\b", 1.2, "after"),
    (r"\b(?:i'?d|i would|would|we'?d|we would) (?:happily |gladly |totally |definitely )?pay (?:good money |so much |anything |extra )?(?:for|to)\b", 1.5, "after"),
    (r"\b(?:looking for|searching for|recommend(?:ations)? for|suggestions for) (?:a|an|some|any)? ?(?:good |cheap |simple |better )?(?:way|app|tool|solution|service|product|alternative)s? (?:to|for|that)\b", 0.9, "after"),
    (r"\bwhy (?:isn'?t|is there no|doesn'?t) there (?:a|an|any)\b", 1.2, "after"),
    (r"\bif only\b", 0.7, "after"),
]

JOY_PATTERNS = [
    (r"\b(?:i|we) (?:absolutely |really |just |honestly |totally )?(?:love|adore|enjoy)\b", 1.0, "after"),
    (r"\b(?:is|was|has been|are|were) (?:a |an |such a |an absolute |a total )?(?:game ?changer|life ?saver|lifesaver|godsend|blessing|life changing|life-changing)\b", 1.3, "before"),
    (r"\b(?:is|was) (?:the |my )?best (?:thing|purchase|decision|investment|app|money)\b", 1.2, "before"),
    (r"\bso (?:happy|glad|grateful|thankful|relieved|proud) (?:with|about|for|that|i)\b", 1.0, "after"),
    (r"\bhighly recommend\b", 1.0, "after"),
    (r"\b(?:finally|at last) (?:found|got|figured out|have|bought|tried)\b", 1.0, "after"),
    (r"\bmakes? me (?:so |really )?(?:happy|smile|feel better)\b", 1.0, "before"),
    (r"\bworth every (?:penny|cent|dollar)\b", 1.2, "before"),
    (r"\bobsessed with\b", 0.9, "after"),
    (r"\bcan'?t live without\b", 1.2, "after"),
    (r"\bmade my (?:day|week|life (?:so much )?easier)\b", 1.1, "before"),
    (r"\b(?:works|worked) (?:perfectly|great|like a charm|wonders)\b", 1.0, "before"),
]

# --- sentiment ---------------------------------------------------------------
POSITIVE = {
    "love": 3, "loved": 3, "loving": 3, "amazing": 3, "awesome": 3, "fantastic": 3, "excellent": 3,
    "perfect": 3, "wonderful": 3, "incredible": 3, "brilliant": 3, "outstanding": 3, "best": 3,
    "great": 2.5, "happy": 2.5, "glad": 2, "grateful": 2.5, "thankful": 2.5, "excited": 2.5,
    "delighted": 3, "joy": 3, "beautiful": 2.5, "lovely": 2.5, "fun": 2, "enjoy": 2, "enjoyed": 2,
    "good": 1.5, "nice": 1.5, "cool": 1.5, "helpful": 2, "useful": 1.5, "easy": 1.5, "easier": 1.5,
    "simple": 1, "fast": 1, "cheap": 1, "affordable": 1.5, "reliable": 2, "recommend": 2,
    "recommended": 2, "worth": 1.5, "win": 2, "proud": 2, "relieved": 2, "relief": 2, "calm": 1.5,
    "comfortable": 1.5, "satisfied": 2, "impressed": 2.5, "favorite": 2, "favourite": 2,
    "gamechanger": 3, "lifesaver": 3, "thanks": 1.5, "thank": 1.5, "fixed": 1.5, "solved": 2,
    "works": 1, "smooth": 1.5, "clean": 1, "healthy": 1.5, "success": 2, "successful": 2,
    "improve": 1.5, "improved": 1.5, "better": 1.5, "wow": 2, "yay": 2, "lol": 0.5, "haha": 1,
    "blessed": 2.5, "fulfilling": 2.5, "peaceful": 2, "obsessed": 1.5, "magic": 2, "superb": 3,
}
NEGATIVE = {
    "hate": -3, "hated": -3, "horrible": -3, "terrible": -3, "awful": -3, "worst": -3,
    "disgusting": -3, "nightmare": -3, "scam": -3, "useless": -2.5, "garbage": -3, "trash": -2.5,
    "bad": -2, "poor": -2, "sad": -2, "angry": -2.5, "mad": -2, "furious": -3, "upset": -2,
    "annoying": -2, "annoyed": -2, "frustrating": -2.5, "frustrated": -2.5, "disappointed": -2.5,
    "disappointing": -2.5, "broken": -2, "broke": -1.5, "crash": -2, "crashes": -2, "crashing": -2,
    "bug": -1.5, "buggy": -2, "slow": -1.5, "expensive": -1.5, "overpriced": -2, "unaffordable": -2.5,
    "confusing": -1.5, "complicated": -1.5, "difficult": -1.5, "hard": -1, "struggle": -2,
    "struggling": -2, "stress": -2, "stressed": -2, "stressful": -2, "anxious": -2, "anxiety": -2,
    "depressed": -2.5, "depressing": -2.5, "lonely": -2, "exhausted": -2, "exhausting": -2,
    "tired": -1.5, "overwhelmed": -2, "overwhelming": -2, "burnout": -2.5, "scared": -2,
    "afraid": -2, "worried": -2, "worry": -1.5, "fear": -2, "pain": -2, "painful": -2.5,
    "hurt": -2, "sick": -1.5, "fail": -2, "failed": -2, "failing": -2, "failure": -2.5,
    "problem": -1.5, "problems": -1.5, "issue": -1, "issues": -1, "waste": -2, "wasted": -2,
    "ripoff": -3, "unfair": -2, "rude": -2, "ignored": -1.5, "lost": -1.5, "losing": -1.5,
    "regret": -2.5, "unusable": -3, "misleading": -2.5, "spam": -2, "ads": -0.5, "paywall": -1.5,
    "cancel": -1, "cancelled": -1.5, "refund": -1.5, "worse": -2, "sucks": -2.5, "suck": -2.5,
    "ugh": -1.5, "wtf": -2, "damn": -1, "crap": -2, "stupid": -2, "ridiculous": -2,
    "impossible": -2, "unbearable": -3, "miserable": -3, "hopeless": -3, "helpless": -2.5,
    "toxic": -2.5, "lazy": -1.5, "boring": -1.5, "fake": -2, "dangerous": -2, "unsafe": -2,
}
NEGATIONS = {"not", "no", "never", "dont", "don't", "doesnt", "doesn't", "didnt", "didn't", "isnt",
             "isn't", "wasnt", "wasn't", "cant", "can't", "cannot", "wont", "won't", "nothing",
             "without", "hardly", "aint", "ain't", "neither", "nor"}
INTENSIFIERS = {"very": 0.3, "really": 0.3, "so": 0.3, "extremely": 0.5, "super": 0.4,
                "incredibly": 0.5, "absolutely": 0.4, "totally": 0.3, "completely": 0.4,
                "utterly": 0.5, "insanely": 0.5, "too": 0.2, "most": 0.3}

# --- keyphrases --------------------------------------------------------------
STOPWORDS = set("""
a about above actually after again against ago all almost also always am amp an and any anyone
anything are aren't around as at away back be became because been before being below between
both but by can can't cannot could couldn't did didn't do does doesn't doing don't done down
during each edit else even ever every everyone everything few find first for from further get
gets getting go goes going gone got gotta had hadn't has hasn't have haven't having he he'd
he'll he's her here here's hers herself him himself his how how's however i i'd i'll i'm i've
id if im in into is isn't it it's its itself ive just know last let let's like little lot lots
made make makes making many may maybe me might mine more most much must mustn't my myself need
needs never new no nor not nothing now of off often oh ok okay on once one ones only or other
others ought our ours ourselves out over own pretty probably put quite rather re really right
said same say says see seem seems seen she she'd she'll she's should shouldn't since so some
someone something sometimes still such sure take tell than that that's the their theirs them
themselves then there there's these they they'd they'll they're they've thing things think this
those though through thx time times to today too took tried try trying u ur under until up upon
us use used using ve very want wanted wants was wasn't way we we'd we'll we're we've well went
were weren't what what's whatever when when's where where's whether which while who who's whom
why why's will with without won't would wouldn't yeah yes yet you you'd you'll you're you've
your yours yourself yourselves across among within toward towards onto per
http https www com amp gt lt nbsp deleted removed via
""".split())

# Words that end an extracted problem/joy object ("struggling with X because ...").
OBJECT_BREAKERS = set("""
because but so when since which while although though until unless whereas cause cuz bc
and then or if as like even after before lol tbh imo anyway
""".split())

# Leading words dropped from extracted objects, so "an app that tracks X" -> "tracks X".
OBJECT_LEAD_DROP = STOPWORDS | {
    "actually", "basically", "literally", "honestly", "seriously", "totally", "tbh", "just", "even",
    "still", "find", "get", "keep", "figure", "deal", "manage", "handle", "stop", "out",
    "app", "apps", "tool", "tools", "way", "service", "website", "site", "product", "program",
    "software", "device", "thing", "something", "anything", "someone", "good", "simple", "better",
}

# Generic words that are never useful as a "most talked about" topic.
TOPIC_STOPWORDS = set("""
year years month months week weeks day days hour hours minute minutes today yesterday tomorrow
people person guy guys lot lots bit kind sort stuff thing things way ways anyone someone
everyone post posts thread reddit sub subreddit comment comments question questions edit update
good bad great best better worse feel feeling felt look looking looks start started help
""".split())

# Objects that carry no meaning on their own.
EMPTY_OBJECTS = {"it", "this", "that", "them", "these", "those", "everything", "anything",
                 "something", "things", "thing", "stuff", "life", "people", "lot", "way", "one",
                 "honestly", "lol", "too", "much", "so much"}
