"""
Central place to maintain Ethiopian holiday recommendation rules.

Update this file when you want to add/remove holidays or change playlist suggestions.
`eth_month` and `eth_day` use Ethiopian calendar values.
"""

HOLIDAY_RULES = [
    {
        "key": "enkutatash",
        "name": "Enkutatash",
        "eth_month": 1,
        "eth_day": 1,
        "recommendations": [
            {
                "playlist_id": "holiday_enkutatash_1",
                "title": "Enkutatash Celebration",
                "reason": "Selected for Ethiopian New Year celebration mood.",
                "tags": ["ethiopian", "holiday", "new-year"],
            },
            {
                "playlist_id": "holiday_enkutatash_2",
                "title": "Fresh Year Vibes",
                "reason": "Upbeat tracks for holiday gatherings.",
                "tags": ["upbeat", "family", "celebration"],
            },
        ],
    },
    {
        "key": "genna",
        "name": "Genna",
        "eth_month": 4,
        "eth_day": 29,
        "recommendations": [
            {
                "playlist_id": "holiday_genna_1",
                "title": "Genna Morning",
                "reason": "Seasonal tracks for Ethiopian Christmas.",
                "tags": ["genna", "spiritual", "ethiopian"],
            },
            {
                "playlist_id": "holiday_genna_2",
                "title": "Warm Holiday Strings",
                "reason": "Calm and festive recommendations for family time.",
                "tags": ["holiday", "acoustic", "calm"],
            },
        ],
    },
    {
        "key": "timket",
        "name": "Timket",
        "eth_month": 5,
        "eth_day": 11,
        "recommendations": [
            {
                "playlist_id": "holiday_timket_1",
                "title": "Timket Procession Mix",
                "reason": "Focused on Timket period listening preferences.",
                "tags": ["timket", "traditional", "ethiopian"],
            },
            {
                "playlist_id": "holiday_timket_2",
                "title": "Festival Reflection",
                "reason": "Reflective tracks for the holiday week.",
                "tags": ["festival", "reflection", "chill"],
            },
        ],
    },
]


DEFAULT_RECOMMENDATIONS = [
    {
        "playlist_id": "daily_discovery_1",
        "title": "Daily Discovery",
        "reason": "No holiday match; using daily fallback.",
        "tags": ["daily", "discovery"],
    },
    {
        "playlist_id": "daily_focus_2",
        "title": "Focus and Flow",
        "reason": "General listening for regular days.",
        "tags": ["focus", "work", "chill"],
    },
]
