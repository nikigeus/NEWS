import feedparser
import os
import datetime
import re
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

# ========== НАСТРОЙКИ ТЕМ ==========
TOPICS = {
    "politics": {
        "name": "Политика",
        "feeds": [
            "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
            "https://www.kommersant.ru/RSS/section-politics.xml"
        ]
    },
    "economy": {
        "name": "Экономика",
        "feeds": [
            "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",
            "https://www.kommersant.ru/RSS/section-economics.xml",
            "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"
        ]
    },
    "science": {
        "name": "Наука",
        "feeds": [
            "https://www.sciencedaily.com/rss/all.xml",
            "https://www.nature.com/nature.rss"
        ]
    },
    "tech": {
        "name": "Техника",
        "feeds": [
            "https://www.kommersant.ru/RSS/section-hitech.xml",
            "https://www.theverge.com/rss/index.xml",
            "https://www.kommersant.ru/RSS/section-auto.xml"
        ]
    },
    "moscow": {
        "name": "Москва",
        "feeds": [
            "https://www.m24.ru/rss.xml",
            "https://lenta.ru/rss/news/moscow"
        ]
    },
    "nnov": {
        "name": "Нижний Новгород",
        "feeds": [
            "https://www.kommersant.ru/rss/regions/nnov_all.xml",
            "https://www.niann.ru/rss"
        ]
    }
}
# ===================================

GIGACHAT_CREDENTIALS = os.environ.get("GIGACHAT_CREDENTIALS")

def fetch_news(feed_urls, limit=5):
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

def ask_gigachat(topic_name, news_list):
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

    try:
        with GigaChat(
            credentials=GIGACHAT_CREDENTIALS,
            verify_ssl_certs=False,
            model="GigaChat-2",  # Базовая быстрая модель. Можно заменить на "GigaChat-2-Pro" для лучшего качества
            timeout=120
        ) as client:
            chat = Chat(messages=[Messages(role=MessagesRole.USER, content=prompt)])
            response = client.chat(chat)
            return response.choices[0].message.content
    except Exception as e:
        print(f"Ошибка GigaChat: {e}")
        return f"Ошибка анализа: {e}"

def main():
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()

    for topic_key, topic_info in TOPICS.items():
        print(f"Обработка темы: {topic_info['name']}")
        news = fetch_news(topic_info["feeds"])

        news_html = ""
        for n in news:
            news_html += f'<div class="news-item"><a href="{n["link"]}" target="_blank">{n["title"]}</a></div>\n'
        if not news_html:
            news_html = "<p>Новости не найдены.</p>"

        analysis_text = ask_gigachat(topic_info["name"], news)
        analysis_html = analysis_text.replace("\n", "<br>")

        pattern_news = f'(<div class="news-list" id="{topic_key}-news">).*?(</div>)'
        html = re.sub(pattern_news, f'\\1\n{news_html}\n\\2', html, flags=re.DOTALL)

        pattern_analysis = f'(<div class="ai-bubble" id="{topic_key}-analysis">).*?(</div>)'
        new_analysis_html = f'\\1\n<h3>Аналитика</h3>\n<p>{analysis_html}</p>\n\\2'
        html = re.sub(pattern_analysis, new_analysis_html, html, flags=re.DOTALL)

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
