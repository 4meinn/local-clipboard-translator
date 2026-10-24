"""The three supported languages and the aliases the language detector may answer with."""

SUPPORTED = ("tr", "de", "en")

ENGLISH_NAME = {"tr": "Turkish", "de": "German", "en": "English"}
NATIVE_NAME = {"tr": "Türkçe", "de": "Deutsch", "en": "English"}

_ALIASES = {
    "tr": "tr", "turkish": "tr", "türkçe": "tr", "turkce": "tr",
    "de": "de", "german": "de", "deutsch": "de",
    "en": "en", "english": "en",
}


def parse_detected(answer):
    """Map the detector's raw answer to ('tr'|'de'|'en', None) or ('other', language name)."""
    word = answer.strip().split("\n")[0].strip().strip(".,;:!\"'`*()[]").lower()
    if word in _ALIASES:
        return _ALIASES[word], None
    return "other", word.title() if word else "this language"
