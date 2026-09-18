"""
Localization system for Dictatly Windows (RU / EN).
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
        "ru": "Перезапустить Dictatly",
        "en": "Restart Dictatly"
    },
    "restarting_service": {
        "ru": "Перезапуск Dictatly...",
        "en": "Restarting Dictatly..."
    },
    "service_restarted": {
        "ru": "Dictatly перезапущен",
        "en": "Dictatly restarted"
    },
    "restart_dictatly": {
        "ru": "Перезапустить Dictatly",
        "en": "Restart Dictatly"
    },
    "restarting_dictatly": {
        "ru": "Перезапуск Dictatly...",
        "en": "Restarting Dictatly..."
    },
    "dictatly_restarted": {
        "ru": "Dictatly перезапущен",
        "en": "Dictatly restarted"
    },
    "stop_service": {
        "ru": "Остановить службу",
        "en": "Stop Service"
    },
    "start_service": {
        "ru": "Запустить службу",
        "en": "Start Service"
    },

    # System & Launch
    "system_section": {
        "ru": "Система и запуск",
        "en": "System & Launch"
    },
    "autostart_with_windows": {
        "ru": "Запускать вместе с Windows",
        "en": "Start with Windows"
    },
    "autostart_with_windows_hint": {
        "ru": "Автоматический запуск службы Dictatly при входе в систему.",
        "en": "Automatically launch Dictatly service upon Windows logon."
    },
    "create_shortcuts": {
        "ru": "Создать ярлыки",
        "en": "Create Shortcuts"
    },
    "create_shortcuts_hint": {
        "ru": "Создает ярлыки на рабочем столе и в меню «Пуск».",
        "en": "Creates shortcuts on Desktop and in Start Menu."
    },
    "shortcuts_created": {
        "ru": "Ярлыки созданы!",
        "en": "Shortcuts created!"
    },

    # Onboarding Dialog
    "welcome_title": {
        "ru": "Добро пожаловать в Dictatly",
        "en": "Welcome to Dictatly"
    },
    "welcome_subtitle": {
        "ru": "Быстрая локальная диктовка и распознавание речи для Windows.",
        "en": "Fast local speech dictation and transcription for Windows."
    },
    "onboarding_how_it_works": {
        "ru": "Как пользоваться диктовкой:",
        "en": "How to use dictation:"
    },
    "onboarding_step1": {
        "ru": "Нажмите <b>Right Ctrl</b> в любом поле ввода для начала записи.",
        "en": "Press <b>Right Ctrl</b> in any text field to start recording."
    },
    "onboarding_step2": {
        "ru": "Произнесите фразу и нажмите <b>Right Ctrl</b> снова для вставки.",
        "en": "Speak your phrase and press <b>Right Ctrl</b> again to insert text."
    },
    "onboarding_step3": {
        "ru": "Нажмите <b>Right Alt + Right Ctrl</b> для открытия истории транскрипций.",
        "en": "Press <b>Right Alt + Right Ctrl</b> to view transcript history."
    },
    "onboarding_autostart_option": {
        "ru": "Запускать вместе с Windows",
        "en": "Start with Windows"
    },
    "onboarding_autostart_desc": {
        "ru": "Фоновая работа в трее, готовность к вводу сразу после входа",
        "en": "Runs quietly in background, ready to dictate upon login"
    },
    "onboarding_shortcuts_option": {
        "ru": "Создать ярлыки на Рабочем столе и в меню «Пуск»",
        "en": "Create Desktop and Start Menu shortcuts"
    },
    "onboarding_shortcuts_desc": {
        "ru": "Быстрый запуск утилиты и доступ к панели истории",
        "en": "Quick access to the app and transcript history panel"
    },
    "onboarding_start_button": {
        "ru": "Начать работу",
        "en": "Get Started"
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

    # Behavior & Recording Mode
    "behavior_section": {
        "ru": "Режим записи и обработка текста",
        "en": "Recording Mode & Text Behavior"
    },
    "recording_mode": {
        "ru": "Режим срабатывания хоткея",
        "en": "Hotkey Trigger Mode"
    },
    "mode_toggle": {
        "ru": "Переключение (нажатие)",
        "en": "Toggle (Click to start/stop)"
    },
    "mode_push_to_talk": {
        "ru": "Удержание (Push-to-Talk)",
        "en": "Push-to-Talk (Hold key)"
    },
    "sound_effects": {
        "ru": "Звуковой сигнал при начале и завершении записи",
        "en": "Audio cues on start and finish"
    },
    "smart_punctuation": {
        "ru": "Умная капитализация первой буквы и очистка пробелов",
        "en": "Smart capitalization & whitespace cleanup"
    },
    "silence_timeout": {
        "ru": "Авто-стоп при длительной тишине",
        "en": "Silence Auto-Stop"
    },
    "timeout_disabled": {
        "ru": "Отключено",
        "en": "Disabled"
    },
    "timeout_10s": {
        "ru": "10 секунд",
        "en": "10 seconds"
    },
    "timeout_15s": {
        "ru": "15 секунд",
        "en": "15 seconds"
    },
    "timeout_30s": {
        "ru": "30 секунд",
        "en": "30 seconds"
    },
    "vocabulary_section": {
        "ru": "Словарь автозамен (термины)",
        "en": "Vocabulary Replacements"
    },
    "vocabulary_hint": {
        "ru": "Формат: слово = замена (по одной паре на строку)",
        "en": "Format: word = replacement (one pair per line)"
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
        "ru": "Dictatly — История и аналитика",
        "en": "Dictatly — History & Analytics"
    },
    "tab_transcripts": {
        "ru": "Записи",
        "en": "Transcripts"
    },
    "tab_analytics": {
        "ru": "Аналитика",
        "en": "Analytics"
    },
    "tab_import": {
        "ru": "Импорт",
        "en": "Import"
    },
    "import_title": {
        "ru": "Пакетная расшифровка аудио",
        "en": "Batch Audio Transcription"
    },
    "import_subtitle": {
        "ru": "Перетащите файлы или выберите их на диске для автоматической расшифровки в .txt",
        "en": "Drag & drop files or browse disk to transcribe automatically into .txt"
    },
    "btn_browse_files": {
        "ru": "Выбрать файлы...",
        "en": "Browse Files..."
    },
    "supported_formats": {
        "ru": "Поддерживаемые форматы:",
        "en": "Supported formats:"
    },
    "source_mic_title": {
        "ru": "Голосовая диктовка",
        "en": "Voice Dictation"
    },
    "source_file_title": {
        "ru": "Файловый импорт",
        "en": "Audio File Import"
    },
    "sources_breakdown_title": {
        "ru": "Распределение источников",
        "en": "Sources Breakdown"
    },
    "analytics_title": {
        "ru": "Продуктивность и статистика",
        "en": "Productivity & Analytics"
    },
    "analytics_subtitle": {
        "ru": "Анализ голосового ввода и сэкономленного времени",
        "en": "Voice dictation insights & saved time"
    },
    "analytics_words_today": {
        "ru": "Слов сегодня",
        "en": "Words Today"
    },
    "analytics_time_saved": {
        "ru": "Сэкономлено времени",
        "en": "Time Saved"
    },
    "analytics_time_saved_sub": {
        "ru": "в ~3.5 раза быстрее печати",
        "en": "~3.5x faster than typing"
    },
    "analytics_speed_wpm": {
        "ru": "Скорость речи",
        "en": "Speaking Pace"
    },
    "analytics_speed_unit": {
        "ru": "сл/мин",
        "en": "wpm"
    },
    "analytics_total_transcripts": {
        "ru": "Всего записей",
        "en": "Total Recordings"
    },
    "analytics_total_words": {
        "ru": "Всего надиктовано",
        "en": "Total Words Dictated"
    },
    "analytics_chart_7d": {
        "ru": "Динамика за 7 дней",
        "en": "7-Day Activity"
    },
    "analytics_chart_hourly": {
        "ru": "По часам сегодня",
        "en": "Hourly Today"
    },
    "analytics_no_data": {
        "ru": "Пока нет данных для графика. Начните надиктовывать текст!",
        "en": "No chart data yet. Start dictating to see your stats!"
    },
    "btn_delete_entry": {
        "ru": "Удалить",
        "en": "Delete"
    },
    "entry_deleted": {
        "ru": "Запись удалена",
        "en": "Entry deleted"
    },
    "time_just_now": {
        "ru": "Только что",
        "en": "Just now"
    },
    "time_mins_ago": {
        "ru": "{mins} мин назад",
        "en": "{mins}m ago"
    },
    "time_hours_ago": {
        "ru": "{hours} ч назад",
        "en": "{hours}h ago"
    },
    "time_yesterday": {
        "ru": "Вчера, {time}",
        "en": "Yesterday, {time}"
    },
    "unit_seconds_short": {
        "ru": "{val:.1f}с",
        "en": "{val:.1f}s"
    },
    "unit_words_short": {
        "ru": "{val} сл.",
        "en": "{val} w."
    },
    "unit_mins_short": {
        "ru": "~{val:.1f} мин",
        "en": "~{val:.1f} min"
    },
    "unit_wpm": {
        "ru": "{val} сл/мин",
        "en": "{val} wpm"
    },
    "unit_words_total": {
        "ru": "{val:,} сл.",
        "en": "{val:,} w."
    },
    "records_today_sub": {
        "ru": "{count} записей за сегодня",
        "en": "{count} recordings today"
    },
    "records_total_sub": {
        "ru": "Всего записей: {count}",
        "en": "Total recordings: {count}"
    },
    "speed_compare_sub": {
        "ru": "vs 40 сл/мин при наборе",
        "en": "vs 40 wpm typing speed"
    },
    "time_saved_multiplier_sub": {
        "ru": "в ~{mult}x быстрее печати",
        "en": "~{mult}x faster than typing"
    },
    "chart_tab_volume": {
        "ru": "Объём",
        "en": "Volume"
    },
    "chart_tab_speed": {
        "ru": "Скорость",
        "en": "Speed"
    },
    "chart_tab_sources": {
        "ru": "Источники",
        "en": "Sources"
    },
    "chart_range_7d": {
        "ru": "7 дней",
        "en": "7 Days"
    },
    "chart_range_14d": {
        "ru": "14 дней",
        "en": "14 Days"
    },
    "chart_range_hourly": {
        "ru": "По часам",
        "en": "Hourly"
    },
    "chart_peak_label": {
        "ru": "Пик",
        "en": "Peak"
    },
    "chart_avg_label": {
        "ru": "В среднем: {val:,} сл/день",
        "en": "Average: {val:,} w/day"
    },
    "chart_speed_avg_label": {
        "ru": "Средний темп: {val} сл/мин",
        "en": "Avg speech pace: {val} wpm"
    },
    "chart_tooltip_words": {
        "ru": "● {val:,} слов",
        "en": "● {val:,} words"
    },
    "chart_tooltip_time_saved": {
        "ru": "~{val:.1f} мин сэкономлено",
        "en": "~{val:.1f} min saved"
    },
    "chart_tooltip_speed": {
        "ru": "{val} сл/мин темп",
        "en": "{val} wpm speech rate"
    },
    "chart_today_badge": {
        "ru": "Сегодня",
        "en": "Today"
    },
    "chart_kb_reference_line": {
        "ru": "40 сл/мин (клавиатура)",
        "en": "40 wpm (keyboard)"
    },
    "source_mic_label": {
        "ru": "Микрофон",
        "en": "Microphone"
    },
    "source_file_label": {
        "ru": "Аудиофайлы",
        "en": "Audio Files"
    },
    "search_placeholder": {
        "ru": "Поиск по расшифровкам...",
        "en": "Search transcripts..."
    },
    "batch_drop_sub": {
        "ru": "Автоматическая расшифровка в .txt",
        "en": "Automatic transcription to .txt"
    },
    "quick_stats_today": {
        "ru": "Сегодня: {words:,} слов  •  ~{mins:.1f} мин сэкономлено  •  {count} записей",
        "en": "Today: {words:,} words  •  ~{mins:.1f} min saved  •  {count} recordings"
    },
    "quick_stats_empty": {
        "ru": "Начните диктовку, чтобы отслеживать продуктивность за сегодня",
        "en": "Start dictating to track your productivity today"
    },
    "copy_click_hint": {
        "ru": "Нажмите для копирования",
        "en": "Click to copy"
    },
    "source_mic": {
        "ru": "Микрофон",
        "en": "Microphone"
    },
    "source_file": {
        "ru": "Файл",
        "en": "File"
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
    "batch_complete": {
        "ru": "Пакетная транскрипция завершена!",
        "en": "Batch transcription complete!"
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
    "tray_pause_hotkeys": {
        "ru": "Приостановить хоткеи (игры / звонки)",
        "en": "Pause Hotkeys (Gaming / Calls)"
    },
    "tray_hotkeys_paused": {
        "ru": "Хоткеи приостановлены",
        "en": "Hotkeys Paused"
    },
    "tray_hotkeys_resumed": {
        "ru": "Хоткеи активны",
        "en": "Hotkeys Active"
    },
    "mic_test_label": {
        "ru": "Тест уровня громкости:",
        "en": "Live Mic Level Test:"
    },
    "tray_toggle_dictation": {
        "ru": "Начать / остановить запись",
        "en": "Toggle Dictation"
    },
    "tray_exit": {
        "ru": "Выход",
        "en": "Exit"
    },
    "app_ready_notification": {
        "ru": "Готов к работе. Нажмите {hotkey} для записи.",
        "en": "Ready. Press {hotkey} to dictate."
    },
    "batch_drop_sub_finished": {
        "ru": "Автоматическая транскрипция и экспорт в .txt",
        "en": "Automatic transcription and export to .txt"
    }
}

def t(msg_key: str, lang: str = "ru", **kwargs) -> str:
    """Get localized string by key."""
    val = STRINGS.get(msg_key, {}).get(lang, STRINGS.get(msg_key, {}).get("ru", msg_key))
    if kwargs:
        return val.format(**kwargs)
    return val
