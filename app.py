# -*- coding: utf-8 -*-
"""
Автопостинг IT-новостей из RSS в Telegram-канал ProLens.
Зависимости:  pip install requests feedparser
"""

import calendar
import hashlib
import html
import json
import logging
import os
import random
import re
import time
from datetime import datetime

import requests
import feedparser

# ======================= НАСТРОЙКИ =====================================

# ▼▼▼ ТОКЕН ▼▼▼
BOT_TOKEN = "7750985599:AAFJ9vQaNnKnqL8lq2RuHrjzcSE1GeRExXw"
CHANNEL_ID = "@ProLensKe"
CHANNEL_URL = "https://t.me/ProLensKe"
CHANNEL_NAME = "ProLens"

# Интервал между проверками (секунды). 30 мин = 1800.
CHECK_INTERVAL = 30 * 60
# Сколько постов максимум за один цикл.
MAX_PER_CYCLE = 3
# Минимальный балл, чтобы опубликовать.
MIN_SCORE = 3
# Новости старше N секунд не публикуем (48 часов).
MAX_NEWS_AGE = 48 * 3600
# Файлы состояния.
SEEN_FILE = "seen_posts.json"
FACTS_FILE = "used_facts.json"
# Лимиты Telegram.
MAX_CAPTION = 1024
MAX_TEXT = 4096
# Присылать ли «бот запущен» в канал.
SEND_STARTUP_MESSAGE = False
# Сколько пустых циклов подряд — и публикуем факт (4 * 30 мин = 2 часа).
EMPTY_CYCLES_BEFORE_FACT = 4

# Вес источников: чем выше — тем охотнее публикуем.
SOURCE_WEIGHTS = {
    "Хабр": 3.0,
    "IXBT": 2.5,
    "3DNews": 2.0,
    "TProger": 2.0,
    "HackerNews": 1.5,
    "Lobsters": 1.0,
    "Reddit /r/programming": 0.5,
}
DEFAULT_SOURCE_WEIGHT = 1.0

RSS_FEEDS = [
    ("Хабр", "https://habr.com/ru/rss/news/?fl=ru"),
    ("TProger", "https://tproger.ru/feed/"),
    ("3DNews", "https://3dnews.ru/news/rss/"),
    ("IXBT", "https://www.ixbt.com/export/news.rss"),
    ("HackerNews", "https://hnrss.org/newest?points=200"),
    ("Lobsters", "https://lobste.rs/rss"),
    ("Reddit /r/programming",
     "https://www.reddit.com/r/programming/top/.rss?t=day"),
]

KEYWORDS_HIGH = [
    "python", "javascript", "typescript", "rust", "golang",
    "java", "kotlin", "swift", "c++", "c#",
    "программир*", "разработ*", "open source", "opensource", "github",
    "нейросет*", "llm", "gpt", "openai", "machine learning",
    "deep learning", "искусственный интеллект", "искусственного интеллекта",
    "алгоритм*", "компилятор*", "фреймворк*",
    "linux", "docker", "kubernetes", "devops",
    "ai", "ml",
]

KEYWORDS_MID = [
    "it", "айти", "технолог*", "tech",
    "software", "софт", "приложени*", "стартап*",
    "developer", "code", "код*", "скрипт*",
    "api", "sdk", "база данных", "базы данных", "database",
    "безопасн*", "уязвим*", "cve",
    "смартфон*", "iphone", "android",
    "обзор*", "релиз*", "обновлени*",
]

STOP_WORDS = [
    "гороскоп*", "реклам*", "скидк*", "распродаж*",
    "купить", "промокод*", "подписывайтесь",
]

CLICKBAIT_WORDS = [
    "шок*", "сенсац*", "вы не поверите", "срочно",
    "просто ужас", "взорвал интернет", "все в шоке",
    "top 10", "топ-10", "10 способов", "лайфхак*",
]

TOPIC_TAGS = [
    ("#python",     ["python"]),
    ("#javascript", ["javascript", "typescript", "node.js", "nodejs"]),
    ("#rust",       ["rust"]),
    ("#golang",     ["golang"]),
    ("#java",       ["java", "kotlin"]),
    ("#ai",         ["нейросет*", "llm", "gpt", "openai",
                     "machine learning", "deep learning",
                     "искусственный интеллект", "artificial intelligence"]),
    ("#linux",      ["linux", "ubuntu", "debian", "kernel"]),
    ("#devops",     ["docker", "kubernetes", "devops"]),
    ("#security",   ["уязвим*", "cve", "взлом*", "хакер*",
                     "ransomware", "безопасн*"]),
    ("#hardware",   ["процессор*", "видеокарт*", "nvidia", "amd",
                     "intel", "чип*", "gpu", "cpu"]),
    ("#mobile",     ["android", "iphone", "ios", "смартфон*"]),
    ("#opensource", ["open source", "opensource", "github"]),
]
MAX_TOPIC_TAGS = 4

INTERESTING_FACTS = [
    "🐍 Python назван в честь «Монти Пайтона», а не в честь змеи.",
    "🖥 Первый компьютерный баг — это реальный мотылёк, застрявший в реле "
    "Mark II в 1947 году.",
    "🌐 Первый сайт в мире — info.cern.ch — до сих пор работает.",
    "📧 Символ @ предложил использовать в email Рэй Томлинсон в 1971 году. "
    "Он же отправил первое в мире письмо по сети — самому себе.",
    "💾 Первый жёсткий диск IBM 305 RAMAC (1956) весил около тонны "
    "и хранил 5 МБ.",
    "⌨️ Клавиатура QWERTY создана в 1870-х, чтобы замедлить печать и "
    "не давать рычагам пишущей машинки залипать.",
    "🧮 Слово «алгоритм» происходит от имени персидского математика "
    "аль-Хорезми (IX век).",
    "🎮 Первая компьютерная игра, Spacewar!, появилась в 1962 году "
    "на компьютере PDP-1.",
    "🔢 В JavaScript 0.1 + 0.2 не равно 0.3 — это не баг, а следствие "
    "стандарта IEEE 754.",
    "🌳 Git создан Линусом Торвальдсом за 2 недели — он просто хотел "
    "заменить BitKeeper.",
    "📱 Самый первый смартфон — IBM Simon (1994). Умел звонить, "
    "принимать факсы и имел тачскрин.",
    "🧠 Термин «искусственный интеллект» придумали в 1956 году "
    "на конференции в Дартмуте.",
    "📡 Первый Wi-Fi стандарт 802.11 вышел в 1997 году, "
    "максимальная скорость — 2 Мбит/с.",
    "🔐 Первый компьютерный вирус Creeper (1971) не вредил — он просто "
    "выводил «I'M THE CREEPER : CATCH ME IF YOU CAN».",
    "💡 Самый дорогой домен в истории — cars.com за $872 млн.",
    "🗄 Язык SQL создан в IBM в 1974 году, назывался SEQUEL — "
    "позже название сократили.",
    "🌍 Первая веб-камера в Кембридже следила за кофеваркой и "
    "обновляла картинку раз в минуту.",
    "🕹 В тетрисе есть скрытый уровень, где фигуры становятся "
    "невидимыми — он включается вручную.",
    "🚀 Первая программа для ракеты была написана в машинных кодах "
    "и содержала 4 000 строк.",
    "🔡 В языке C нет ни одного зарезервированного слова для "
    "ввода-вывода — всё делается через библиотечные функции.",
]

# ======================= ЛОГИ ==========================================

LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bot.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
log = logging.getLogger("autopost")

API = "https://api.telegram.org/bot" + BOT_TOKEN

# ======================= КЛЮЧЕВЫЕ СЛОВА ================================

def compile_keywords(words):
    patterns = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if w.endswith("*"):
            stem = re.escape(w[:-1])
            patterns.append(re.compile(r"(?<![\w])" + stem, re.IGNORECASE))
        else:
            exact = re.escape(w)
            patterns.append(
                re.compile(r"(?<![\w])" + exact + r"(?![\w])", re.IGNORECASE))
    return patterns


RE_HIGH = compile_keywords(KEYWORDS_HIGH)
RE_MID = compile_keywords(KEYWORDS_MID)
RE_STOP = compile_keywords(STOP_WORDS)
RE_CLICKBAIT = compile_keywords(CLICKBAIT_WORDS)
RE_TOPICS = [(tag, compile_keywords(words)) for tag, words in TOPIC_TAGS]

# ======================= TELEGRAM ======================================

def tg_call(method, timeout=20, **data):
    for attempt in range(3):
        try:
            r = requests.post(API + "/" + method, data=data, timeout=timeout)
            resp = r.json()
        except Exception as e:
            log.warning("Telegram/%s: %s (попытка %d/3)",
                        method, e, attempt + 1)
            time.sleep(5)
            continue
        if resp.get("ok"):
            return resp
        if resp.get("error_code") == 429:
            wait = resp.get("parameters", {}).get("retry_after", 5)
            log.warning("Флуд-контроль, жду %s сек", wait)
            time.sleep(wait + 1)
            continue
        return resp
    return {"ok": False, "description": "3 неудачные попытки"}


def tg_get_me():
    try:
        r = requests.get(API + "/getMe", timeout=15)
        return r.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}


def tg_get_chat(chat_id):
    try:
        r = requests.get(API + "/getChat",
                         params={"chat_id": chat_id}, timeout=15)
        return r.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}


def subscribe_line():
    return ('📢 Подписаться: <a href="%s"><b>%s</b></a>'
            % (CHANNEL_URL, CHANNEL_NAME))


def make_keyboard(link):
    if not link:
        return None
    return json.dumps({
        "inline_keyboard": [[
            {"text": "🔗 Читать полностью", "url": link},
            {"text": "📢 Подписаться", "url": CHANNEL_URL},
        ]]
    }, ensure_ascii=False)


def tg_send_message(chat_id, text, link=None, keyboard=True):
    data = {
        "chat_id": chat_id,
        "text": text[:MAX_TEXT],
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    if keyboard:
        kb = make_keyboard(link)
        if kb:
            data["reply_markup"] = kb
    return tg_call("sendMessage", **data)


def tg_send_photo(chat_id, photo_url, caption, link=None):
    data = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }
    kb = make_keyboard(link)
    if kb:
        data["reply_markup"] = kb
    return tg_call("sendPhoto", timeout=30, **data)


def publish(text, image, link):
    if image and len(text) <= MAX_CAPTION - 10:
        resp = tg_send_photo(CHANNEL_ID, image, text, link)
        if resp.get("ok"):
            return resp
        log.warning("Фото не отправилось (%s), шлю текстом",
                    resp.get("description"))
    return tg_send_message(CHANNEL_ID, text, link)

# ======================= ИСТОРИЯ =======================================

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set(), []
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(data), []
        return set(data.get("ids", [])), list(data.get("titles", []))
    except Exception:
        return set(), []


def save_seen(seen_ids, seen_titles):
    try:
        with open(SEEN_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "ids": list(seen_ids)[-1500:],
                "titles": seen_titles[-300:],
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("Ошибка сохранения истории: %s", e)


def load_used_facts():
    if not os.path.exists(FACTS_FILE):
        return []
    try:
        with open(FACTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_used_facts(used):
    try:
        with open(FACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(used[-len(INTERESTING_FACTS):], f,
                      ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("Ошибка сохранения фактов: %s", e)


def pick_fact(used):
    remaining = [f for f in INTERESTING_FACTS if f not in used]
    if not remaining:
        used.clear()
        remaining = list(INTERESTING_FACTS)
    fact = random.choice(remaining)
    used.append(fact)
    return fact

# ======================= ТЕКСТ =========================================

def make_id(entry):
    raw = entry.get("link") or entry.get("title", "")
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def shorten(text, limit=250):
    if len(text) <= limit:
        return text
    cut = text[:limit]
    dot = cut.rfind(".")
    if dot > limit // 2:
        return cut[:dot + 1] + " ..."
    return cut + " ..."


def normalize_title(title):
    t = re.sub(r"[^0-9a-zа-яё ]", " ", title.lower())
    return re.sub(r"\s+", " ", t).strip()


def title_tokens(title):
    return set(normalize_title(title).split())


def is_duplicate(title, known_titles, threshold=0.55):
    tok = title_tokens(title)
    if not tok:
        return False
    for other in known_titles:
        ot = title_tokens(other)
        if not ot:
            continue
        union = len(tok | ot)
        if union and len(tok & ot) / union >= threshold:
            return True
    return False


def find_image(entry):
    media = entry.get("media_content") or []
    if media and isinstance(media, list):
        url = media[0].get("url")
        if url:
            return url
    thumb = entry.get("media_thumbnail") or []
    if thumb and isinstance(thumb, list):
        url = thumb[0].get("url")
        if url:
            return url
    for enc in (entry.get("enclosures") or []):
        if enc.get("type", "").startswith("image"):
            return enc.get("href") or enc.get("url")
    summary = entry.get("summary", "")
    if summary:
        m = re.search(r'<img[^>]+src="([^"]+)"', summary)
        if m:
            return m.group(1)
    return None


def entry_timestamp(entry):
    if entry.get("published_parsed"):
        try:
            return calendar.timegm(entry["published_parsed"])
        except Exception:
            pass
    if entry.get("updated_parsed"):
        try:
            return calendar.timegm(entry["updated_parsed"])
        except Exception:
            pass
    return time.time()

# ======================= ОЦЕНКА НОВОСТИ ================================

def score_entry(entry, source):
    title = clean_html(entry.get("title", ""))
    summary = clean_html(entry.get("summary", ""))
    text = title + " " + summary

    score = 0.0
    reasons = []

    kw_score = 0
    for p in RE_HIGH:
        if p.search(text):
            kw_score += 3
    for p in RE_MID:
        if p.search(text):
            kw_score += 1
    for p in RE_STOP:
        if p.search(text):
            kw_score -= 2
    kw_score = max(min(kw_score, 9), -4)
    score += kw_score
    if kw_score > 0:
        reasons.append("kw+%d" % kw_score)
    elif kw_score < 0:
        reasons.append("kw%d" % kw_score)

    sw = SOURCE_WEIGHTS.get(source, DEFAULT_SOURCE_WEIGHT)
    score += sw
    reasons.append("src+%.1f" % sw)

    age = max(0, time.time() - entry_timestamp(entry))
    if age < 3600:
        fresh = 3.0
    elif age < 6 * 3600:
        fresh = 2.0
    elif age < 24 * 3600:
        fresh = 1.0
    elif age < MAX_NEWS_AGE:
        fresh = 0.0
    else:
        fresh = -3.0
    score += fresh
    if fresh:
        reasons.append("fresh+%.1f" % fresh)

    if find_image(entry):
        score += 1.0
        reasons.append("img+1")

    slen = len(summary)
    if 100 <= slen <= 600:
        score += 1.0
        reasons.append("desc+1")
    elif slen < 40:
        score -= 0.5
        reasons.append("desc-0.5")

    if len(title) >= 30:
        score += 0.5
        reasons.append("title+0.5")

    for p in RE_CLICKBAIT:
        if p.search(text):
            score -= 3.0
            reasons.append("clickbait-3")
            break

    return score, reasons


def topic_tags(entry):
    text = (entry.get("title", "") + " " +
            clean_html(entry.get("summary", "")))
    tags = []
    for tag, patterns in RE_TOPICS:
        if any(p.search(text) for p in patterns):
            tags.append(tag)
        if len(tags) >= MAX_TOPIC_TAGS:
            break
    return tags

# ======================= ОФОРМЛЕНИЕ ====================================

def build_post(entry, source):
    title = html.escape(clean_html(entry.get("title", "Без названия")))
    summary = html.escape(clean_html(entry.get("summary", "")))
    date_str = datetime.fromtimestamp(
        entry_timestamp(entry)).strftime("%d.%m.%Y %H:%M")

    tags = " ".join(["#новости", "#IT"] + topic_tags(entry))

    parts = ["💻 <b>%s</b>" % title, ""]
    if summary:
        parts.append(shorten(summary, 280))
        parts.append("")
    parts += [
        "🕐 %s" % date_str,
        "📡 %s" % source,
        "",
        tags,
        "",
        "━━━━━━━━━━━━━━",
        subscribe_line(),
    ]
    return "\n".join(parts)


def build_fact_post(fact):
    return "\n".join([
        "💡 <b>Интересный факт</b>",
        "",
        fact,
        "",
        "━━━━━━━━━━━━━━",
        subscribe_line(),
    ])

# ======================= RSS ===========================================

def fetch_feed(url):
    try:
        r = requests.get(url, timeout=15,
                         headers={"User-Agent":
                                  "Mozilla/5.0 (autopost-bot)"})
        r.raise_for_status()
        return feedparser.parse(r.content)
    except Exception as e:
        log.warning("RSS не загрузился: %s — %s", url, e)
        return None


def collect_candidates(seen_ids, seen_titles):
    candidates = []
    now = time.time()
    for source, url in RSS_FEEDS:
        log.info("Источник: %s", source)
        feed = fetch_feed(url)
        if not feed or not feed.entries:
            continue
        for entry in feed.entries[:15]:
            eid = make_id(entry)
            if eid in seen_ids:
                continue
            if now - entry_timestamp(entry) > MAX_NEWS_AGE:
                seen_ids.add(eid)
                continue
            title = clean_html(entry.get("title", ""))
            if is_duplicate(title, seen_titles):
                log.info("Дубль, пропускаю: %s", title[:60])
                seen_ids.add(eid)
                continue
            sc, reasons = score_entry(entry, source)
            if sc >= MIN_SCORE:
                candidates.append((sc, entry, source, eid, reasons))
                log.info("  [%.1f] %s (%s) — %s",
                         sc, title[:50], source, ",".join(reasons))
        time.sleep(1)
    return candidates

# ======================= ГЛАВНЫЙ ЦИКЛ ==================================

def loop(state):
    seen_ids = state["ids"]
    seen_titles = state["titles"]
    used_facts = state["facts"]
    empty_cycles = 0

    log.info("Автопостинг запущен. Интервал: %d мин",
             CHECK_INTERVAL // 60)
    log.info("История: %d постов", len(seen_ids))

    while True:
        posted_something = False
        try:
            candidates = collect_candidates(seen_ids, seen_titles)
            if not candidates:
                log.info("Подходящих новостей нет.")
            else:
                log.info("Нашёл подходящих: %d", len(candidates))
                candidates.sort(
                    key=lambda item: (item[0], entry_timestamp(item[1])),
                    reverse=True)

                posted_this_cycle = []
                for sc, entry, src, eid, reasons in candidates[:MAX_PER_CYCLE]:
                    title = clean_html(entry.get("title", ""))
                    if is_duplicate(title, seen_titles + posted_this_cycle):
                        seen_ids.add(eid)
                        continue
                    text = build_post(entry, src)
                    image = find_image(entry)
                    link = entry.get("link", "")
                    resp = publish(text, image, link)
                    if resp.get("ok"):
                        seen_ids.add(eid)
                        seen_titles.append(title)
                        posted_this_cycle.append(title)
                        posted_something = True
                        log.info("Опубликовано [%.1f]: %s",
                                 sc, title[:60])
                    else:
                        log.error("Ошибка отправки: %s",
                                  resp.get("description"))
                    time.sleep(3)

                save_seen(seen_ids, seen_titles)

            if posted_something:
                empty_cycles = 0
            else:
                empty_cycles += 1
                log.info("Пустых циклов подряд: %d/%d",
                         empty_cycles, EMPTY_CYCLES_BEFORE_FACT)
                if empty_cycles >= EMPTY_CYCLES_BEFORE_FACT:
                    fact = pick_fact(used_facts)
                    save_used_facts(used_facts)
                    resp = tg_send_message(
                        CHANNEL_ID, build_fact_post(fact), keyboard=False)
                    if resp.get("ok"):
                        log.info("Опубликован факт: %s", fact[:50])
                    else:
                        log.error("Ошибка отправки факта: %s",
                                  resp.get("description"))
                    empty_cycles = 0

        except Exception as e:
            log.error("Ошибка в цикле: %s", e)

        log.info("Следующая проверка через %d мин",
                 CHECK_INTERVAL // 60)
        time.sleep(CHECK_INTERVAL)

# ======================= ЗАПУСК ========================================

def main():
    log.info("Запускаюсь...")
    if not BOT_TOKEN:
        log.error("Не задан BOT_TOKEN!")
        return

    me = tg_get_me()
    if not me.get("ok"):
        log.error("Ошибка токена: %s", me.get("description"))
        return
    log.info("Бот: @%s", me["result"]["username"])

    chat = tg_get_chat(CHANNEL_ID)
    if not chat.get("ok"):
        log.error("Не могу получить канал: %s", chat.get("description"))
        log.error("Добавь бота в админы канала %s.", CHANNEL_ID)
        return
    log.info("Канал: %s", chat["result"].get("title"))

    if SEND_STARTUP_MESSAGE:
        tg_send_message(
            CHANNEL_ID,
            "✅ <b>Автопостинг запущен</b>\n\n"
            "Публикую IT-новости каждые %d мин.\n\n%s"
            % (CHECK_INTERVAL // 60, subscribe_line()),
            keyboard=False)

    ids, titles = load_seen()
    facts = load_used_facts()
    state = {"ids": ids, "titles": titles, "facts": facts}
    try:
        loop(state)
    finally:
        save_seen(state["ids"], state["titles"])
        save_used_facts(state["facts"])
        log.info("История сохранена.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Остановлено.")