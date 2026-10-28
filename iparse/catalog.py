"""Built-in catalog of groups of people and where they talk online.

Each group has a segment dimension ("audience" for who people are, "interest"
for what they're into, "region" for where they live) and the communities to
collect from on each source. The same table drives collection and segment
labelling, so a post from r/nursing is tagged audience:healthcare workers.

Groups marked sensitive (health, sexuality) are only collected when
`include_sensitive = true` in [catalog]. They are labelled at community
level only; nothing about an individual author is inferred.

Subreddit names that don't exist are skipped with a warning, so it's safe to
add guesses. Use `iparse discover <keyword>` to find more.
"""
from __future__ import annotations


def G(dim, reddit=(), se=(), mastodon=(), apps=(), sensitive=False):
    return {"dim": dim, "reddit": list(reddit), "se": list(se), "mastodon": list(mastodon),
            "apps": list(apps), "sensitive": sensitive}


CATALOG: dict[str, dict] = {
    # ------------------------------------------------------------ family & age
    "parents": G("audience", ["Parenting", "Mommit", "daddit", "toddlers", "NewParents", "beyondthebump", "Parents"],
                 ["parenting"], ["parenting"], ["baby tracker", "family organizer", "kids screen time"]),
    "expecting parents": G("audience", ["pregnant", "BabyBumps", "TryingForABaby"], apps=["pregnancy"]),
    "single parents": G("audience", ["SingleParents", "singlemoms"]),
    "teens": G("audience", ["teenagers", "highschool", "ApplyingToCollege"]),
    "college students": G("audience", ["college", "UniUK", "StudentLoans", "studytips", "GetStudying", "CollegeRant"],
                          mastodon=["students"], apps=["study planner", "flashcards"]),
    "grad students & academics": G("audience", ["GradSchool", "PhD", "AskAcademia"], ["academia"], ["academia", "phdlife"]),
    "young adults": G("audience", ["Adulting", "findapath", "LifeAdvice"]),
    "older adults & retirees": G("audience", ["retirement", "AskOldPeople", "over40", "EarlyRetirement"], apps=["medicare"]),
    "women (community)": G("audience", ["AskWomen", "TwoXChromosomes", "AskWomenOver30"]),
    "men (community)": G("audience", ["AskMen", "AskMenOver30", "MensLib", "malelivingspace"]),
    "caregivers": G("audience", ["CaregiverSupport", "AgingParents"], apps=["caregiver"]),
    "immigrants & expats": G("audience", ["IWantOut", "expats", "immigration"], ["expatriates"]),
    "low income": G("audience", ["povertyfinance", "foodstamps"]),
    "LGBTQ+ (community)": G("audience", ["lgbt", "asktransgender", "actuallesbians", "askgaybros"], sensitive=True),
    "disabled people (community)": G("audience", ["disability", "ChronicIllness", "blind", "deaf"],
                                     mastodon=["disability"], sensitive=True),
    # ---------------------------------------------------------------- work
    "tech workers": G("audience", ["cscareerquestions", "ExperiencedDevs", "sysadmin", "ITCareerQuestions", "webdev"],
                      ["softwareengineering"], ["devops"]),
    "healthcare workers": G("audience", ["nursing", "medicine", "residency", "pharmacy", "ems", "physicaltherapy"],
                            mastodon=["nursing"]),
    "teachers": G("audience", ["Teachers", "teaching", "education"], mastodon=["teachers", "edutooters"],
                  apps=["classroom"]),
    "trades": G("audience", ["electricians", "Plumbing", "Construction", "HVAC", "Welding", "Carpentry"]),
    "drivers & gig workers": G("audience", ["Truckers", "uberdrivers", "doordash_drivers", "couriersofreddit",
                                            "InstacartShoppers"], apps=["delivery driver"]),
    "hospitality workers": G("audience", ["KitchenConfidential", "TalesFromYourServer", "serverlife", "bartenders",
                                          "barista"]),
    "retail workers": G("audience", ["TalesFromRetail", "retailhell"]),
    "office & corporate": G("audience", ["humanresources", "Accounting", "sales", "projectmanagement", "consulting",
                                         "Lawyertalk"], ["workplace"]),
    "small business owners": G("audience", ["smallbusiness", "Entrepreneur", "startups", "ecommerce", "shopify",
                                            "EtsySellers", "restaurateur"], ["startups"], ["smallbusiness"],
                               ["invoice", "point of sale", "small business"]),
    "freelancers & creators": G("audience", ["freelance", "NewTubers", "WorkOnline", "freelanceWriters", "Upwork",
                                             "graphic_design"], mastodon=["freelance"], apps=["content creator"]),
    "job seekers": G("audience", ["jobs", "recruitinghell", "resumes", "careerguidance", "GetEmployed"],
                     apps=["job search"]),
    "remote workers": G("audience", ["remotework", "digitalnomad", "WFH"]),
    "farmers & homesteaders": G("audience", ["farming", "homestead", "agriculture"]),
    "military & veterans": G("audience", ["Military", "Veterans", "army", "AirForce", "navy"]),
    "real estate agents": G("audience", ["realtors"]),
    # ------------------------------------------------------- money & housing
    "personal finance": G("audience", ["personalfinance", "financialindependence", "Debt", "CreditCards"],
                          ["money"], ["personalfinance"], ["budget", "credit score"]),
    "budget-conscious": G("audience", ["Frugal", "BuyItForLife", "EatCheapAndHealthy"], apps=["coupons", "cashback"]),
    "home buyers & owners": G("audience", ["FirstTimeHomeBuyer", "homeowners", "RealEstate"], apps=["mortgage"]),
    "renters": G("audience", ["Renting", "Apartmentliving", "roommates", "Landlord"]),
    # -------------------------------------------------------- life situations
    "relationships & dating": G("audience", ["dating", "dating_advice", "relationship_advice", "Marriage", "Divorce",
                                             "weddingplanning"], apps=["dating", "wedding planner"]),
    "pet owners": G("audience", ["dogs", "cats", "puppy101", "DogTraining", "Pets"], ["pets"], ["dogs", "cats"],
                    ["pet care", "dog training"]),
    "travelers": G("interest", ["travel", "solotravel", "TravelHacks", "Shoestring"], ["travel"], ["travel"],
                   ["travel planner", "flights"]),
    "self-improvement": G("interest", ["selfimprovement", "getdisciplined", "productivity", "DecidingToBeBetter"],
                          ["lifehacks"], ["productivity"], ["habit tracker", "to do list", "journal"]),
    "mental health (community)": G("audience", ["mentalhealth", "Anxiety", "ADHD", "depression"],
                                   apps=["meditation", "therapy"], sensitive=True),
    "chronic health (community)": G("audience", ["ChronicPain", "diabetes", "migraine", "ibs"], sensitive=True),
    # -------------------------------------------------------------- interests
    "fitness": G("interest", ["Fitness", "bodyweightfitness", "xxfitness", "GYM", "homegym"], ["fitness"], ["fitness"],
                 ["fitness tracker", "workout"]),
    "weight loss & nutrition": G("interest", ["loseit", "nutrition", "intermittentfasting", "1200isplenty"],
                                 apps=["calorie counter"]),
    "running & cycling": G("interest", ["running", "bicycling", "cycling", "triathlon"], ["bicycles"], ["running"],
                           ["running"]),
    "cooking & food": G("interest", ["Cooking", "MealPrepSunday", "AskCulinary", "Baking", "slowcooking"],
                        ["cooking"], ["cooking"], ["meal planner", "recipes", "grocery list"]),
    "gaming": G("interest", ["gaming", "pcgaming", "PS5", "NintendoSwitch", "patientgamers", "gamedev"],
                ["gamedev"], ["gaming"]),
    "tech & gadgets": G("interest", ["technology", "gadgets", "apple", "Android", "techsupport", "buildapc",
                                     "homeautomation"], ["superuser", "android"], ["tech"], ["password manager", "vpn"]),
    "cars": G("interest", ["cars", "MechanicAdvice", "whatcarshouldIbuy", "electricvehicles", "Cartalk"],
              ["mechanics"], apps=["car maintenance", "ev charging"]),
    "home & DIY": G("interest", ["HomeImprovement", "DIY", "woodworking", "InteriorDesign", "CleaningTips",
                                 "organization"], ["diy"], ["diy"], ["home inventory"]),
    "gardening & plants": G("interest", ["gardening", "houseplants", "plantclinic", "vegetablegardening",
                                         "landscaping"], ["gardening"], ["gardening"], ["plant care"]),
    "outdoors": G("interest", ["camping", "hiking", "CampingandHiking", "Fishing", "hunting", "vandwellers"],
                  ["outdoors"], ["hiking"], ["hiking"]),
    "fashion & beauty": G("interest", ["femalefashionadvice", "malefashionadvice", "SkincareAddiction",
                                       "MakeupAddiction", "curlyhair", "beauty"], apps=["skincare"]),
    "creative hobbies": G("interest", ["crafts", "knitting", "sewing", "photography", "WeAreTheMusicMakers", "writing",
                                       "ArtistLounge"], ["photo", "writing"], ["knitting", "photography"]),
    "books & learning": G("interest", ["books", "languagelearning", "learnprogramming", "duolingo",
                                       "suggestmeabook"], ["languagelearning"], ["books"], ["language learning"]),
    "music & entertainment": G("interest", ["Music", "movies", "television", "podcasts", "anime"],
                               apps=["podcast", "music streaming"]),
    "sports fans": G("interest", ["sports", "nba", "soccer", "nfl", "golf", "tennis"], apps=["sports scores"]),
    "investing & crypto": G("interest", ["investing", "stocks", "Bogleheads", "CryptoCurrency"],
                            ["quant"], apps=["investing"]),
    "sustainability": G("interest", ["ZeroWaste", "sustainability", "solar", "Anticonsumption"],
                        ["sustainability"], ["climate"]),
    "board games & tabletop": G("interest", ["boardgames", "DnD", "magicTCG"], ["boardgames", "rpg"], ["ttrpg"]),
    # ---------------------------------------------------------------- regions
    "United States": G("region", ["AskAnAmerican"]),
    "United Kingdom": G("region", ["unitedkingdom", "AskUK", "UKPersonalFinance", "CasualUK", "LegalAdviceUK"]),
    "Canada": G("region", ["canada", "AskACanadian", "PersonalFinanceCanada", "canadahousing"]),
    "Australia": G("region", ["australia", "AusFinance", "AskAnAustralian"]),
    "India": G("region", ["india", "indiasocial", "IndiaInvestments", "developersIndia"]),
    "Ireland": G("region", ["ireland", "irishpersonalfinance"]),
    "New Zealand": G("region", ["newzealand", "PersonalFinanceNZ"]),
    "Philippines": G("region", ["Philippines", "phinvest", "CasualPH"]),
    "Nigeria": G("region", ["Nigeria"]),
    "South Africa": G("region", ["southafrica", "PersonalFinanceZA"]),
    "Singapore": G("region", ["singapore", "singaporefi"]),
    "Germany": G("region", ["germany", "AskAGerman"]),
}


def select(groups: list[str] | None, include_sensitive: bool = False) -> dict[str, dict]:
    """Groups to collect. ["*"] = all (minus sensitive unless included). Also accepts
    dimension names ("audience", "interest", "region") and "-name" to exclude."""
    groups = groups if groups is not None else ["*"]
    chosen: dict[str, dict] = {}
    for g in groups:
        if g.startswith("-"):
            continue
        if g == "*":
            chosen.update({k: v for k, v in CATALOG.items() if include_sensitive or not v["sensitive"]})
        elif g in ("audience", "interest", "region"):
            chosen.update({k: v for k, v in CATALOG.items()
                           if v["dim"] == g and (include_sensitive or not v["sensitive"])})
        elif g in CATALOG:
            chosen[g] = CATALOG[g]
        else:
            raise ValueError(f"Unknown catalog group {g!r}. Run `iparse catalog` to list them.")
    for g in groups:
        if g.startswith("-"):
            chosen.pop(g[1:], None)
    return chosen


def community_segments() -> dict[str, list[str]]:
    """community key (lowercase) -> segment tags, for every catalog group."""
    out: dict[str, list[str]] = {}

    def add(key, tag):
        tags = out.setdefault(key.lower(), [])
        if tag not in tags:
            tags.append(tag)

    for name, g in CATALOG.items():
        tag = f"{g['dim']}:{name}"
        for sub in g["reddit"]:
            add(f"r/{sub}", tag)
        for site in g["se"]:
            add(f"se/{site}", tag)
        for t in g["mastodon"]:
            add(f"#{t}", tag)
        for term in g["apps"]:
            add(f"appstore:{term}", tag)
    return out
