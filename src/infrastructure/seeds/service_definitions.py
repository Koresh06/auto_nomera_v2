from src.domain.enums.publication_service import PublicationServiceType


DEFAULT_SERVICES = [
    {
        "type": PublicationServiceType.HIGHLIGHT,
        "title": "Красная рамка",
        "price": 20000,
        "duration_days": None,
        "description": "Выделяет объявление красной рамкой",
    },
    {
        "type": PublicationServiceType.PIN,
        "title": "Закрепление",
        "price": 50000,
        "duration_days": 3,
        "description": "Закрепляет объявление в канале на 3 дня",
    },
    {
        "type": PublicationServiceType.AUTOPUBLISH,
        "title": "Автопубликация 7 дней",
        "price": 100000,
        "duration_days": 7,
        "description": "Публикует объявление 7 дней подряд",
    },
    {
        "type": PublicationServiceType.PRIORITY_PUBLISH,
        "title": "Опубликовать сейчас",
        "price": 30000,
        "duration_days": None,
        "description": "Публикует объявление прямо сейчас",
    },
    {
        "type": PublicationServiceType.PRE_PUBLICATION,
        "title": "Объявление до публикации",
        "price": 50000,
        "duration_days": 30,
        "description": "Доступ к каталогу за 2 часа до публикации на 30 дней",
    },
]
