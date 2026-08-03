"""Local fallback content generators for script and SEO metadata."""


def build_script(topic: str) -> str:
    return f"""
Hook: {topic} पर आज का सबसे ज़रूरी अपडेट

Intro:
आज हम आपको {topic} के बारे में सरल भाषा में समझाएंगे।

Step 1:
सबसे पहले आपको जानकारी की मूल बात समझनी होगी।

Step 2:
फिर इसे अपने लिए लागू करना सीखें।

Step 3:
अंत में सबसे जरूरी सुझाव जानें।

Summary:
यह अपडेट आपके लिए महत्वपूर्ण हो सकता है।

CTA:
अगर आप चाहें, तो मैं इसे और आसान तरीके से भी समझा सकता हूँ।
"""


def build_seo(topic: str) -> dict:
    return {
        "title": f"{topic} | आसान समझ में",
        "description": f"{topic} पर आसान और उपयोगी जानकारी।",
        "hashtags": "#government #india #updates #news",
        "tags": [topic, "government update", "india"],
    }
