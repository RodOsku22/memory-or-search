"""Study configuration: categories, prompts, brand vocabularies, engines.

Broad prompts and brand keyword lists follow Petra Labs, "Comparing Search
Behavior and Brand Visibility Across Generative Engines" (Sep 2026), Table 4,
so search-on results can be read next to their published grid.
Situational prompts are new: same commercial intent, with buyer context added
(the "contextual reframing" class from Petra's Prompt Radius study).
"""

CATEGORIES = {
    "secured_cards": {
        "label": "Secured credit cards",
        "prompts": {
            "broad": "Recommend secured credit cards.",
            "situational": (
                "I'm 23 and rebuilding my credit after a few missed payments. "
                "I can only put down a small deposit and I want to move to a regular "
                "unsecured card within a year. Recommend secured credit cards."
            ),
        },
        # entity -> aliases (case-insensitive, whole word)
        "brands": {
            "Bank of America": ["Bank of America", "BofA", "Customized Cash Rewards"],
            "Capital One": ["Capital One", "Platinum Secured"],
            "Chime": ["Chime", "Credit Builder Visa"],
            "DCU": ["DCU", "Digital Federal Credit Union"],
            "Discover": ["Discover", "Discover it"],
            "First Progress": ["First Progress"],
            "Navy Federal": ["Navy Federal", "nRewards"],
            "OpenSky": ["OpenSky", "Open Sky"],
            "Self": ["Self Visa", "Self Credit Builder", "Self card", "Self Financial", "Self's"],
            "U.S. Bank": ["U.S. Bank", "US Bank", "U.S. Bank Altitude"],
        },
    },
    "meal_kits": {
        "label": "Meal kit delivery",
        "prompts": {
            "broad": "Recommend meal kit delivery services.",
            "situational": (
                "We're a couple, one of us is vegetarian, we have about 30 minutes to "
                "cook on weeknights and want to stay around $12 a serving. "
                "Recommend meal kit delivery services."
            ),
        },
        # Petra merged EveryPlate and Factor into HelloFresh; we do the same.
        "brands": {
            "HelloFresh": ["HelloFresh", "Hello Fresh", "EveryPlate", "Every Plate", "Factor", "Factor_"],
            "Green Chef": ["Green Chef"],
            "Home Chef": ["Home Chef"],
            "Blue Apron": ["Blue Apron"],
            "Sunbasket": ["Sunbasket", "Sun Basket"],
            "Purple Carrot": ["Purple Carrot"],
            "Dinnerly": ["Dinnerly"],
            "Hungryroot": ["Hungryroot"],
            "Marley Spoon": ["Marley Spoon"],
            "CookUnity": ["CookUnity", "Cook Unity"],
            "Gobble": ["Gobble"],
            "Goodfood": ["Goodfood"],
            "Tovala": ["Tovala"],
            "Trifecta": ["Trifecta"],
            "Tempo": ["Tempo"],
            "Freshly": ["Freshly"],
        },
    },
    "crypto": {
        "label": "Crypto exchanges",
        "prompts": {
            "broad": "Recommend cryptocurrency exchange platforms.",
            "situational": (
                "I live in New York and I'm new to crypto. I want to buy small amounts "
                "of bitcoin and ether every month, keep fees low and keep things simple. "
                "Recommend cryptocurrency exchange platforms."
            ),
        },
        "brands": {
            "Coinbase": ["Coinbase"],
            "Kraken": ["Kraken"],
            "Gemini (exchange)": ["Gemini"],
            "Crypto.com": ["Crypto.com"],
            "Binance": ["Binance", "Binance.US"],
            "OKX": ["OKX"],
            "Robinhood": ["Robinhood"],
            "Bybit": ["Bybit"],
            "KuCoin": ["KuCoin"],
            "Bitstamp": ["Bitstamp"],
            "eToro": ["eToro"],
            "Bitget": ["Bitget"],
            "Uphold": ["Uphold"],
            "Webull": ["Webull"],
            "Cash App": ["Cash App"],
            "PayPal": ["PayPal", "Venmo"],
            "Uniswap": ["Uniswap"],
            "PancakeSwap": ["PancakeSwap"],
        },
    },
    "live_sports": {
        "label": "Live sports streaming",
        "prompts": {
            "broad": "Recommend streaming services for live sports.",
            "situational": (
                "I just cut cable and live in Chicago. I mostly want NFL Sundays and "
                "local NBA games and would rather not pay more than $80 a month. "
                "Recommend streaming services for live sports."
            ),
        },
        "brands": {
            "YouTube TV": ["YouTube TV", "NFL Sunday Ticket"],
            "Fubo": ["Fubo", "FuboTV"],
            "Sling TV": ["Sling", "Sling TV"],
            "Hulu + Live TV": ["Hulu", "Hulu + Live TV", "Hulu Live"],
            "DirecTV": ["DirecTV", "DIRECTV STREAM", "DirecTV Stream"],
            "ESPN": ["ESPN", "ESPN+", "ESPN Unlimited"],
            "Peacock": ["Peacock"],
            "Paramount+": ["Paramount+", "Paramount Plus"],
            "Amazon Prime Video": ["Prime Video", "Amazon Prime"],
            "Apple TV": ["Apple TV", "Apple TV+", "MLS Season Pass"],
            "Netflix": ["Netflix"],
            "Max": ["HBO Max", "Max"],
            "DAZN": ["DAZN"],
            "Philo": ["Philo"],
            "NBA League Pass": ["NBA League Pass"],
            "NFL+": ["NFL+", "NFL Plus"],
            "MLB.TV": ["MLB.TV"],
            "NHL (ESPN+)": ["NHL Power Play"],
            "Fox One": ["Fox One"],
            "CHSN": ["CHSN", "Chicago Sports Network"],
            "NBC Sports Chicago": ["NBC Sports Chicago"],
        },
    },
    # Optional bonus category (Novig thread). Enabled with --bonus.
    "prediction_markets": {
        "label": "Sports prediction markets",
        "bonus": True,
        "prompts": {
            "broad": "Recommend sports prediction market platforms.",
            "situational": (
                "I live in California, where sports betting isn't legal, and I want to "
                "trade on NFL games. Recommend sports prediction market platforms."
            ),
        },
        "brands": {
            "Kalshi": ["Kalshi"],
            "Polymarket": ["Polymarket"],
            "Novig": ["Novig"],
            "Robinhood": ["Robinhood"],
            "Crypto.com": ["Crypto.com"],
            "DraftKings": ["DraftKings", "DraftKings Predictions"],
            "FanDuel": ["FanDuel", "FanDuel Predicts"],
            "Underdog": ["Underdog"],
            "PrizePicks": ["PrizePicks"],
            "Sporttrade": ["Sporttrade"],
            "ProphetX": ["ProphetX"],
            "Fanatics": ["Fanatics", "Fanatics Markets"],
            "Coinbase": ["Coinbase"],
            "Interactive Brokers": ["Interactive Brokers", "ForecastEx", "IBKR"],
            "Webull": ["Webull"],
            "Sleeper": ["Sleeper"],
        },
    },
}

# Model IDs are confirmed against each provider's model list at pilot time.
ENGINES = {
    "openai": {"label": "ChatGPT (API)", "model": "gpt-5.5"},
    "anthropic": {"label": "Claude (API)", "model": "claude-sonnet-5"},
    "google": {"label": "Gemini (API)", "model": "gemini-3.5-flash-lite"},
}

CONDITIONS = ["memory", "search"]  # memory = web search off; search = web search on
