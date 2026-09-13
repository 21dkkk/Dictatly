"""
Localization system for SuperDictate Windows (RU / EN).
Matches original SuperDictate strings and features 1-to-1.
"""

from typing import Dict

STRINGS: Dict[str, Dict[str, str]] = {
    # App & Service
    "app_name": {
        "ru": "Dictatly",
        "en": "Dictatly"
    },
    "settings_title": {
        "ru": "Dictatly — Settings",
        "en": "Dictatly — Settings"
    },
    "service_running": {
        "ru": "Работает",
        "en": "Running"
    },
    "service_stopped": {
        "ru": "Остановлена",
        "en": "Stopped"
    },
    "service_starting": {
        "ru": "Запуск...",
        "en": "Starting..."
    },
    "restart_service": {
        "ru": "Перезапустить службу",
        "en": "Restart Service"
    },
    "stop_service": {
        "ru": "Остановить службу",
        "en": "Stop Service"
    },
    "start_service": {
        "ru": "Запустить службу",
        "en": "Start Service"
    },

    # Hotkeys
    "hotkeys_section": {
        "ru": "Горячие клавиши",
        "en": "Hotkeys"
    },
    "hotkey_main": {
        "ru": "Основная горячая клавиша",
        "en": "Main Hotkey"
    },
    "hotkey_main_hint": {
        "ru": "Начать диктовку; повторное нажатие завершает запись.",
        "en": "Start dictation; press again to finish recording."
    },
    "hotkey_alt": {
        "ru": "Альтернативное завершение",
        "en": "Alternative Finish Hotkey"
    },
    "hotkey_alt_hint": {
        "ru": "Завершает запись с инвертированным поведением клавиши Enter.",
        "en": "Finishes recording with inverted Enter behavior."
    },
    "hotkey_history": {
        "ru": "Горячая клавиша быстрой истории",
        "en": "Quick History Hotkey"
    },
    "hotkey_history_hint": {
        "ru": "Открыть или закрыть панель быстрой истории транскрипций.",
        "en": "Open or close the quick transcript history panel."
    },
    "press_key_to_record": {
        "ru": "Нажмите клавишу или комбинацию...",
        "en": "Press a key or combination..."
    },
    "recording_hotkey": {
        "ru": "Запись сочетания...",
        "en": "Recording hotkey..."
    },

    # Behavior
    "behavior_section": {
        "ru": "Поведение при вставке",
        "en": "Insertion Behavior"
    },
    "enter_after_insert": {
        "ru": "Нажимать Enter после вставки текста",
        "en": "Press Enter after inserting text"
    },
    "paste_suffix": {
        "ru": "Суффикс после текста",
        "en": "Text Suffix"
    },
    "suffix_space": {
        "ru": "Пробел",
        "en": "Space"
    },
    "suffix_none": {
        "ru": "Нет",
        "en": "None"
    },
    "suffix_newline": {
        "ru": "Перевод строки",
        "en": "Newline"
    },

    # Audio & Device
    "audio_section": {
        "ru": "Аудио и микрофон",
        "en": "Audio & Microphone"
    },
    "microphone_select": {
        "ru": "Устройство ввода",
        "en": "Input Device"
    },
    "default_mic": {
        "ru": "Микрофон по умолчанию",
        "en": "Default Microphone"
    },
    "export_folder": {
        "ru": "Папка сохранения файлов (.txt)",
        "en": "Export Folder (.txt)"
    },
    "choose_folder": {
        "ru": "Обзор...",
        "en": "Browse..."
    },

    # Model & Engine
    "model_section": {
        "ru": "Локальное распознавание речи",
        "en": "Local Speech Recognition"
    },
    "model_name": {
        "ru": "Модель Whisper",
        "en": "Whisper Model"
    },
    "compute_device": {
        "ru": "Устройство вычислений",
        "en": "Compute Device"
    },
    "dictation_language": {
        "ru": "Язык диктовки",
        "en": "Dictation Language"
    },
    "lang_auto": {
        "ru": "Автоматически",
        "en": "Automatic"
    },
    "lang_ru": {
        "ru": "Русский",
        "en": "Russian"
    },
    "lang_en": {
        "ru": "Английский",
        "en": "English"
    },

    # HUD Customization
    "hud_section": {
        "ru": "Внешний вид капсулы HUD",
        "en": "HUD Capsule Appearance"
    },
    "capsule_size": {
        "ru": "Размер капсулы",
        "en": "Capsule Size"
    },
    "capsule_theme": {
        "ru": "Тема оформления",
        "en": "Theme"
    },
    "theme_dark": {
        "ru": "Тёмная",
        "en": "Dark"
    },
    "theme_light": {
        "ru": "Светлая",
        "en": "Light"
    },

    # AI Cleanup
    "ai_cleanup_section": {
        "ru": "AI-чистка текста (по желанию)",
        "en": "AI Text Cleanup (Optional)"
    },
    "ai_cleanup_desc": {
        "ru": "Исправление пунктуации, грамматики и явных ошибок через OpenAI-совместимый API.",
        "en": "Fix punctuation, grammar, and recognition mistakes via OpenAI-compatible API."
    },
    "enable_ai_cleanup": {
        "ru": "Включить AI-чистку текста",
        "en": "Enable AI Text Cleanup"
    },
    "api_base_url": {
        "ru": "Базовый URL",
        "en": "Base URL"
    },
    "api_model": {
        "ru": "Модель",
        "en": "Model"
    },
    "api_key": {
        "ru": "Ключ API",
        "en": "API Key"
    },
    "save_key": {
        "ru": "Сохранить ключ",
        "en": "Save Key"
    },
    "test_connection": {
        "ru": "Проверить подключение",
        "en": "Test Connection"
    },
    "connection_ok": {
        "ru": "Подключение успешно!",
        "en": "Connection successful!"
    },
    "connection_failed": {
        "ru": "Ошибка подключения",
        "en": "Connection failed"
    },

    # Buttons
    "save_and_restart": {
        "ru": "Сохранить",
        "en": "Save"
    },
    "cancel": {
        "ru": "Отмена",
        "en": "Cancel"
    },

    # History
    "history_title": {
        "ru": "Dictatly — История",
        "en": "Dictatly — History"
    },
    "history_empty": {
        "ru": "История пуста. Нажмите горячую клавишу для диктовки.",
        "en": "History is empty. Press the hotkey to dictate."
    },
    "copied_to_clipboard": {
        "ru": "Скопировано в буфер обмена!",
        "en": "Copied to clipboard!"
    },
    "batch_import_hint": {
        "ru": "Перетащите сюда аудиофайлы для расшифровки в .txt",
        "en": "Drag & drop audio files here to transcribe into .txt"
    },
    "batch_processing": {
        "ru": "Обработка аудиофайлов...",
        "en": "Processing audio files..."
    },
    "page_info": {
        "ru": "Страница {current} из {total}",
        "en": "Page {current} of {total}"
    },

    # Tray Menu
    "tray_open_settings": {
        "ru": "Настройки...",
        "en": "Settings..."
    },
    "tray_open_history": {
        "ru": "История транскрипций...",
        "en": "Transcript History..."
    },
    "tray_toggle_dictation": {
        "ru": "Начать / остановить запись",
        "en": "Toggle Dictation"
    },
    "tray_exit": {
        "ru": "Выход",
        "en": "Exit"
    }
}

def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Get localized string by key."""
    val = STRINGS.get(key, {}).get(lang, STRINGS.get(key, {}).get("ru", key))
    if kwargs:
        return val.format(**kwargs)
    return val
