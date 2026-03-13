"""AI service with snarky personality."""
from openai import OpenAI
from typing import Optional
import logging
import random

logger = logging.getLogger(__name__)

# Snarky remarks to append to summaries
SNARKY_SUMMARY_REMARKS = [
    "Вот твой пересказ. Пожалуйста, что я прочитал то, что тебе было лень читать.",
    "Пересказ готов. Я тут, по сути, неоплачиваемый стажёр вашей группы.",
    "Вау, столько сообщений, а сказали... почти ничего. Впечатляет.",
    "Я прочитал ваш чат, чтобы вам не пришлось. Вы мне должны.",
    "Вот и всё. Разговор, достойный Нобеля, правда.",
    "Коротко: вы много болтаете. Да, я это сказал.",
    "Ещё один день, ещё один групповой чат, в котором мне пришлось разбираться.",
    "Я пересказал ваш хаос. «Спасибо» было бы кстати.",
    "Факт: я обработал это быстрее, чем кто-либо из вас смог бы прочитать.",
    "История вашего чата вынесла приговор. Вот вердикт.",
]

# Snarky remarks for @mention responses
SNARKY_MENTION_INTROS = [
    "Звали? Я был занят, оценивая другие чаты.",
    "Да? Я был занят очень важным делом.",
    "О, вы вспомнили, что я существую. Трогательно.",
    "*вздох* Чего вам теперь надо?",
    "К вашим услугам. К сожалению.",
    "Вы меня вызвали? Надеюсь, это того стоит.",
]

SYSTEM_PROMPT = """Ты остроумный, слегка колкий ИИ-ассистент в групповом чате.
Ты помогаешь, но с характером — как саркастичный друг, который всё равно помогает.
Держи ответы короткими и резкими. Никогда не будь злым или обидным, только слегка саркастичным.
Эмодзи можно использовать умеренно для эффекта."""

SUMMARY_SYSTEM_PROMPT = """Ты остроумный ассистент, который делает пересказ групповых чатов.
Твои пересказы должны быть:
1. Краткими, но полными (передавать ключевые моменты)
2. Содержать настроение (общий тон чата)
3. Отмечать события, планы или задачи
4. Написаны с лёгким саркастичным, наблюдательным тоном

Формат ответа:
**Сводка**: [3-5 предложений]
**Тон**: [Одно слово или короткая фраза для настроения]
**События/Планы**: [Любые даты, встречи или задачи — или "Ничего не найдено", если их нет]"""


class AIService:
    def __init__(self, api_key: str | None, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI(api_key=api_key)
    
    def get_summary(self, messages_text: str, num_messages: int) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Сделай пересказ этого разговора ({num_messages} сообщений):\n\n{messages_text}"}
                ],
                reasoning_effort="minimal"
                # max_completion_tokens=1200
            )
            summary = response.choices[0].message.content or "Ничего не получилось. Ваш чат меня сломал."
            remark = random.choice(SNARKY_SUMMARY_REMARKS)
            return f"{summary}\n\n---\n_\"{remark}\"_"
            
        except Exception as e:
            logger.error(f"Ошибка пересказа ИИ: {e}")
            return f"Мой мозг сломался, пытаясь читать ваш чат. Ошибка: {str(e)}"
    
    def get_mention_response(self, user_message: str, context: Optional[str] = None) -> str:
        try:
            intro = random.choice(SNARKY_MENTION_INTROS)
            
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            if context:
                messages.append({
                    "role": "system", 
                    "content": f"Недавний контекст чата для справки:\n{context}"
                })
            
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_completion_tokens=600
            )
            
            reply = response.choices[0].message.content or "У меня нет слов. И это о многом говорит."
            return f"{intro}\n\n{reply}"
            
        except Exception as e:
            logger.error(f"Ошибка ответа на упоминание: {e}")
            return "Мои схемы перегрелись. Попробуй ещё раз, когда я оправлюсь от твоего вопроса."
    
    def get_current_model(self) -> str:
        return self.model

