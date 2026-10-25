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
        "chk_clickable": "Let me pet the character: click it for hearts",
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
        "grp_performance": "Performance",
        "lbl_processor": "Translate using",
        "proc_gpu": "GPU (graphics card)",
        "proc_cpu": "CPU (processor)",
        "note_gpu": "Fastest, usually 1 to 3 seconds. Uses graphics card memory while the model is loaded, "
                    "which can slow down games and other GPU-heavy apps.",
        "note_cpu": "Slower, often 5 to 15 seconds. Uses your processor while translating but leaves the "
                    "graphics card free, so games and video stay smooth.",
        "lbl_keep_alive": "Free memory when idle after",
        "unit_minutes": " min",
        "run_gpu": "Loaded now: {model} on the GPU.",
        "run_cpu": "Loaded now: {model} on the CPU.",
        "run_mixed": "Loaded now: {model}, {pct}% on the GPU and the rest on the CPU (slower).",
        "run_none": "The model is not loaded right now. It loads when you copy something.",
        "grp_general": "General",
        "chk_autostart": "Start with Windows",
        "lbl_ui_language": "Interface language",
        "ui_auto": "Automatic",
        "hint_copy": "Copy any text to see it translated.",
        "msg_too_long": "That text is too long ({n} characters, the limit is {max}). Please copy something shorter.",
        "msg_ollama_down": "Ollama is not running. Please start it and copy the text again.",
        "msg_no_model": "No model is installed. Run: ollama pull gemma2:9b",
        "msg_model_missing": "Model \"{model}\" is not installed. Run: ollama pull {model}",
        "msg_error": "Translation failed. Please try again.",
        "msg_unsupported": "Sorry, {lang} is not supported.",
        "msg_paused": "Translating is paused. Turn it back on from the tray menu.",
        "tray_tooltip_paused": "Local Clipboard Translator (paused)",
        "msg_loading_model": "Loading the translation model. The first time can take a minute...",
        "msg_hotkey_busy": "The hotkey {key} is already used by another program. Please pick a different one in the settings.",
        "tray_history": "History",
        "tray_history_empty": "(empty)",
        "tray_history_clear": "Clear history",
        "grp_trigger": "When to translate",
        "trig_auto": "Every time I copy text",
        "trig_double": "When I copy the same text twice",
        "trig_hotkey": "When I press a hotkey (after copying)",
        "lbl_hotkey": "Hotkey",
        "note_trig_auto": "The simplest way, but code or file paths you copy get translated too.",
        "note_trig_double": "Press Ctrl+C twice on the same text within a moment. Single copies are left alone.",
        "note_trig_hotkey": "Copy as usual, then press the hotkey. Nothing is translated until you do.",
        "chk_pause_fullscreen": "Pause translating and walk off screen while a game or fullscreen app is in front",
        "btn_setup": "Set up Ollama...",
        "tray_setup": "Set up Ollama...",
        "wiz_title": "Set up translation",
        "wiz_checking": "Checking your computer...",
        "wiz_need_ollama": "Ollama is not installed. It is the free program that runs the translation "
                           "model on your own computer, so nothing you copy ever leaves it.\n\n"
                           "Download it from ollama.com{size} and install it now?",
        "size_mb": " (about {n} MB)",
        "size_gb": " (about {n} GB)",
        "wiz_btn_install": "Download and install",
        "wiz_downloading": "Downloading Ollama...",
        "wiz_installing": "Installing Ollama, this can take a minute...",
        "wiz_starting": "Starting Ollama...",
        "wiz_need_model": "Ollama is ready, but no translation model is installed yet.\n\n"
                          "Download {model}{size}? It is a one-time download. Later you can install any "
                          "other model with Ollama and pick it in the settings.",
        "wiz_btn_model": "Download model",
        "wiz_pulling": "Downloading {model}...",
        "wiz_done": "All set! Copy any text and the character will translate it.",
        "wiz_btn_close": "Close",
        "wiz_btn_later": "Not now",
        "wiz_btn_retry": "Try again",
        "wiz_error": "Something went wrong:\n{err}",
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
        "chk_clickable": "Karakteri sevebileyim: tıklayınca kalpler çıksın",
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
        "grp_performance": "Performans",
        "lbl_processor": "Çeviri şununla yapılsın",
        "proc_gpu": "GPU (ekran kartı)",
        "proc_cpu": "CPU (işlemci)",
        "note_gpu": "En hızlısı, genelde 1-3 saniye. Model yüklüyken ekran kartı belleğini kullanır, "
                    "bu yüzden oyunları ve ekran kartını çok kullanan uygulamaları yavaşlatabilir.",
        "note_cpu": "Daha yavaş, çoğunlukla 5-15 saniye. Çeviri sırasında işlemciyi kullanır ama ekran "
                    "kartını boş bırakır, oyun ve video akıcı kalır.",
        "lbl_keep_alive": "Boşta kalınca belleği boşalt",
        "unit_minutes": " dk",
        "run_gpu": "Şu an yüklü: {model}, GPU'da.",
        "run_cpu": "Şu an yüklü: {model}, CPU'da.",
        "run_mixed": "Şu an yüklü: {model}, %{pct} GPU'da, kalanı CPU'da (daha yavaş).",
        "run_none": "Model şu an yüklü değil. Bir şey kopyalayınca yüklenir.",
        "grp_general": "Genel",
        "chk_autostart": "Windows ile birlikte başlat",
        "lbl_ui_language": "Arayüz dili",
        "ui_auto": "Otomatik",
        "hint_copy": "Çevirmek için herhangi bir metni kopyala.",
        "msg_too_long": "Bu metin çok uzun ({n} karakter, sınır {max}). Lütfen daha kısa bir metin kopyala.",
        "msg_ollama_down": "Ollama çalışmıyor. Lütfen başlatıp metni tekrar kopyala.",
        "msg_no_model": "Kurulu model yok. Şunu çalıştır: ollama pull gemma2:9b",
        "msg_model_missing": "\"{model}\" modeli kurulu değil. Şunu çalıştır: ollama pull {model}",
        "msg_error": "Çeviri başarısız oldu. Lütfen tekrar dene.",
        "msg_unsupported": "Maalesef {lang} desteklenmiyor.",
        "msg_paused": "Çeviri duraklatıldı. Tepsi menüsünden tekrar açabilirsin.",
        "tray_tooltip_paused": "Local Clipboard Translator (duraklatıldı)",
        "msg_loading_model": "Çeviri modeli yükleniyor. İlk seferde bir dakika sürebilir...",
        "msg_hotkey_busy": "{key} kısayolunu başka bir program kullanıyor. Lütfen ayarlardan farklı bir kısayol seç.",
        "tray_history": "Geçmiş",
        "tray_history_empty": "(boş)",
        "tray_history_clear": "Geçmişi temizle",
        "grp_trigger": "Ne zaman çevrilsin",
        "trig_auto": "Her metin kopyaladığımda",
        "trig_double": "Aynı metni iki kez kopyalayınca",
        "trig_hotkey": "Kısayol tuşuna basınca (kopyaladıktan sonra)",
        "lbl_hotkey": "Kısayol tuşu",
        "note_trig_auto": "En basit yol, ama kopyaladığın kod ya da dosya yolları da çevrilir.",
        "note_trig_double": "Aynı metin üzerinde kısa sürede iki kez Ctrl+C yap. Tek kopyalamalara dokunulmaz.",
        "note_trig_hotkey": "Her zamanki gibi kopyala, sonra kısayola bas. Sen basana kadar hiçbir şey çevrilmez.",
        "chk_pause_fullscreen": "Oyun ya da tam ekran uygulama varken çeviriyi duraklat ve ekrandan çık",
        "btn_setup": "Ollama kurulumu...",
        "tray_setup": "Ollama kurulumu...",
        "wiz_title": "Çeviri kurulumu",
        "wiz_checking": "Bilgisayarın kontrol ediliyor...",
        "wiz_need_ollama": "Ollama kurulu değil. Çeviri modelini kendi bilgisayarında çalıştıran ücretsiz "
                           "bir programdır, bu yüzden kopyaladığın hiçbir şey bilgisayarından çıkmaz.\n\n"
                           "ollama.com'dan{size} indirip şimdi kuralım mı?",
        "size_mb": " (yaklaşık {n} MB)",
        "size_gb": " (yaklaşık {n} GB)",
        "wiz_btn_install": "İndir ve kur",
        "wiz_downloading": "Ollama indiriliyor...",
        "wiz_installing": "Ollama kuruluyor, bir dakika sürebilir...",
        "wiz_starting": "Ollama başlatılıyor...",
        "wiz_need_model": "Ollama hazır ama henüz kurulu bir çeviri modeli yok.\n\n"
                          "{model}{size} indirilsin mi? Tek seferlik bir indirme. Sonradan Ollama ile "
                          "istediğin başka bir modeli kurup ayarlardan seçebilirsin.",
        "wiz_btn_model": "Modeli indir",
        "wiz_pulling": "{model} indiriliyor...",
        "wiz_done": "Hazır! Herhangi bir metni kopyala, karakter çevirsin.",
        "wiz_btn_close": "Kapat",
        "wiz_btn_later": "Şimdi değil",
        "wiz_btn_retry": "Tekrar dene",
        "wiz_error": "Bir şeyler ters gitti:\n{err}",
    },
}

# Shown when the copied text is in a supported language that is not part of the chosen pair.
# Written in that language so the reader understands it.
NOT_IN_PAIR = {
    "en": "Sorry, English is not part of your current pair ({a} - {b}). You can change it in settings.",
    "tr": "Maalesef Türkçe şu anki dil çiftinde yok ({a} - {b}). Ayarlardan değiştirebilirsin.",
    "de": "Leider gehört Deutsch nicht zu deinem aktuellen Sprachpaar ({a} - {b}). Du kannst es in den Einstellungen ändern.",
}


# Said when the character walks off because a fullscreen app took over. It follows the
# Windows display language, not the app's interface language setting; anything else gets English.
FAREWELL = {
    "tr": "İyi eğlenceler, sonra görüşürüz!",
    "de": "Viel Spaß, bis später!",
    "en": "Have fun, see you later!",
}

_PRIMARY_LANGUAGE_IDS = {0x1F: "tr", 0x07: "de", 0x09: "en"}


def windows_language():
    """'tr', 'de' or 'en' from the Windows display language, 'en' for anything else."""
    try:
        import ctypes
        langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
    except (AttributeError, OSError, ImportError):
        return "en"
    return _PRIMARY_LANGUAGE_IDS.get(langid & 0x3FF, "en")


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
