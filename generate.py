import feedparser
import requests
import os
import datetime
import re

# ========== НАСТРОЙКИ: добавьте или измените темы и RSS-источники здесь ==========
TOPICS = {
    "tech": {
        "name": "Технологии",
        "feeds": [
            "https://feeds.arstechnica.com/arstechnica/technology-lab",
            "https://www.theverge.com/rss/index.xml"
        ]
    },
    "science": {
        "name": "Наука",
        "feeds": [
            "https://www.sciencedaily.com/rss/all.xml",
            "https://www.nature.com/nature.rss"
        ]
    }
}
# ==============================================================================

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

def fetch_news(feed_urls, limit=5):
    """Получить последние новости из списка RSS-лент, максимум limit штук с каждой ленты."""
    all_news = []
    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit]:
                all_news.append({
                    "title": entry.get("title", "Без заголовка"),
                    "link": entry.get("link", "#"),
                    "summary": entry.get("summary", entry.get("description", ""))[:300]
                })
        except Exception as e:
            print(f"Ошибка при чтении {url}: {e}")
    return all_news

def ask_deepseek(topic_name, news_list):
    """Отправить новости в DeepSeek, получить аналитическое резюме."""
    if not news_list:
        return "Нет новостей для анализа."

    news_text = "\n".join([f"- {n['title']}: {n['summary']}" for n in news_list])

    prompt = f"""Ты — аналитик новостей. На основе предоставленных ниже новостей по теме "{topic_name}" составь краткую сводку на русском языке:
1. Что произошло (главные события)
2. К чему всё идёт (тенденции)
3. Какие прогнозы дают источники

Пиши кратко, по делу, без воды.

Новости:
{news_text}"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "stream": False
    }

    try:
        resp = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Ошибка DeepSeek: {e}")
        return f"Ошибка анализа: {e}"

def main():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    for topic_key, topic_info in TOPICS.items():
        print(f"Обработка темы: {topic_info['name']}")
        news = fetch_news(topic_info["feeds"])

        # Сгенерировать HTML-список новостей
        news_html = ""
        for n in news:
            news_html += f'<div class="news-item"><a href="{n["link"]}" target="_blank">{n["title"]}</a></div>\n'
        if not news_html:
            news_html = "<p>Новости не найдены.</p>"

        # Вызвать DeepSeek для анализа
        analysis_text = ask_deepseek(topic_info["name"], news)
        # Простая обработка переносов строк
        analysis_html = analysis_text.replace("\n", "<br>")

        # Вставить в HTML
        pattern_news = f'(<div class="news-list" id="{topic_key}-news">).*?(</div>)'
        html = re.sub(pattern_news, f'\\1\n{news_html}\n\\2', html, flags=re.DOTALL)

        pattern_analysis = f'(<div class="analysis" id="{topic_key}-analysis">).*?(</div>)'
        html = re.sub(pattern_analysis, f'\\1\n<h3>Анализ</h3>\n<p>{analysis_html}</p>\n\\2', html, flags=re.DOTALL)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    html = html.replace(
        '<div class="timestamp" id="timestamp"></div>',
        f'<div class="timestamp" id="timestamp">Последнее обновление: {now}</div>'
    )

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Готово. index.html обновлён.")

if __name__ == "__main__":
    main()
