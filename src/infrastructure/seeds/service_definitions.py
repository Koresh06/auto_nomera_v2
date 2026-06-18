from src.domain.enums.publication_service import PublicationServiceType


DEFAULT_SERVICES = [
    {
        "type": PublicationServiceType.PRE_PUBLICATION,
        "title": "💎 Объявления до публикации | Выкуп.",
        "price": 200,
        "duration_days": 30,
        "description": "Вы получите доступ к объявлениям из раздела срочный выкуп и доступ к объявлениям до публикации на канале.",
    },
    {
        "type": PublicationServiceType.PRIORITY_PUBLISH,
        "title": "🥇 Вне очереди",
        "price": 200,
        "duration_days": None,
        "description": "Ваше объявление будет опубликовано «здесь и сейчас» на канале.",
    },
    {
        "type": PublicationServiceType.HIGHLIGHT,
        "title": "🟥 Выделение",
        "price": 200,
        "duration_days": None,
        "description": "Ваше объявление будет выделяться среди сотен других объявлений.",
    },
    {
        "type": PublicationServiceType.PIN,
        "title": "📌 Закрепление",
        "price": 500,
        "duration_days": 3,
        "description": "Ваше объявление будет закреплено на самом видном месте канала.",
    },
    {
        "type": PublicationServiceType.AUTOPUBLISH,
        "title": "🔂 Автопубликация",
        "price": 5000,
        "duration_days": 7,
        "description": "Ваше объявление будет автоматически публиковаться ежедневно в одно и тоже время.",
    },
]
