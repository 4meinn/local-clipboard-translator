"""UI strings. English is the fallback for anything a language does not define."""
import locale

STRINGS = {
    "en": {
        "tray_tooltip": "Local Clipboard Translator",
        "tray_settings": "Settings",
        "tray_pause": "Pause translating",
        "tray_resume": "Resume translating",
        "tray_quit": "Quit",
        "win_title": "Local Clipboard Translator",
        "grp_languages": "Languages",
        "lbl_lang_a": "Language A",
        "lbl_lang_b": "Language B",
        "lang_hint": "Text you copy in one language is translated into the other.",
        "grp_character": "Character",
        "lbl_size": "Size",
        "grp_bubble": "Speech bubble",
        "chk_selectable": "Let me select and copy the translation text",
        "lbl_duration": "Show for",
        "unit_seconds": " s",
        "grp_model": "Model",
        "lbl_model": "Ollama model",
        "model_auto": "Automatic (best installed)",
        "btn_refresh": "Refresh",
        "status_ok": "Ollama is running, {n} model(s) installed.",
        "status_down": "Ollama is not running. Start the Ollama app and press Refresh.",
        "grp_general": "General",
        "chk_autostart": "Start with Windows",
        "lbl_ui_language": "Interface language",
        "ui_auto": "Automatic",
        "hint_copy": "Copy any text to see it translated.",
        "msg_too_long": "That text is too long ({n} characters, the limit is {max}). Please copy something shorter.",
        "msg_ollama_down": "Ollama is not running. Please start it and copy the text again.",
        "msg_no_model": "No model is installed. Run: ollama pull qwen3:8b",
        "msg_model_missing": "Model \"{model}\" is not installed. Run: ollama pull {model}",
        "msg_error": "Translation failed. Please try again.",
        "msg_unsupported": "Sorry, {lang} is not supported.",
        "msg_paused": "Translating is paused.",
    },
    "tr": {
        "tray_settings": "Ayarlar",
        "tray_pause": "Çeviriyi duraklat",
        "tray_resume": "Çeviriye devam et",
        "tray_quit": "Çıkış",
        "grp_languages": "Diller",
        "lbl_lang_a": "Dil A",
        "lbl_lang_b": "Dil B",
        "lang_hint": "Bir dilde kopyaladığın metin diğer dile çevrilir.",
        "grp_character": "Karakter",
        "lbl_size": "Boyut",
        "grp_bubble": "Konuşma balonu",
        "chk_selectable": "Çeviri metnini seçip kopyalayabileyim",
        "lbl_duration": "Görünme süresi",
        "unit_seconds": " sn",
        "grp_model": "Model",
        "lbl_model": "Ollama modeli",
        "model_auto": "Otomatik (kurulu en iyi model)",
        "btn_refresh": "Yenile",
        "status_ok": "Ollama çalışıyor, {n} model kurulu.",
        "status_down": "Ollama çalışmıyor. Ollama uygulamasını başlatıp Yenile'ye bas.",
        "grp_general": "Genel",
        "chk_autostart": "Windows ile birlikte başlat",
        "lbl_ui_language": "Arayüz dili",
        "ui_auto": "Otomatik",
        "hint_copy": "Çevirmek için herhangi bir metni kopyala.",
        "msg_too_long": "Bu metin çok uzun ({n} karakter, sınır {max}). Lütfen daha kısa bir metin kopyala.",
        "msg_ollama_down": "Ollama çalışmıyor. Lütfen başlatıp metni tekrar kopyala.",
        "msg_no_model": "Kurulu model yok. Şunu çalıştır: ollama pull qwen3:8b",
        "msg_model_missing": "\"{model}\" modeli kurulu değil. Şunu çalıştır: ollama pull {model}",
        "msg_error": "Çeviri başarısız oldu. Lütfen tekrar dene.",
        "msg_unsupported": "Maalesef {lang} desteklenmiyor.",
        "msg_paused": "Çeviri duraklatıldı.",
    },
}

# Shown when the copied text is in a supported language that is not part of the chosen pair.
# Written in that language so the reader understands it.
NOT_IN_PAIR = {
    "en": "Sorry, English is not part of your current pair ({a} - {b}). You can change it in settings.",
    "tr": "Maalesef Türkçe şu anki dil çiftinde yok ({a} - {b}). Ayarlardan değiştirebilirsin.",
    "de": "Leider gehört Deutsch nicht zu deinem aktuellen Sprachpaar ({a} - {b}). Du kannst es in den Einstellungen ändern.",
}


def resolve_ui_language(setting):
    if setting in STRINGS:
        return setting
    try:
        system = (locale.getlocale()[0] or "").lower()
    except ValueError:
        system = ""
    return "tr" if system.startswith(("tr", "turkish")) else "en"


class Translator:
    def __init__(self, language="en"):
        self.language = language

    def __call__(self, key, **kwargs):
        text = STRINGS.get(self.language, {}).get(key) or STRINGS["en"][key]
        return text.format(**kwargs) if kwargs else text
