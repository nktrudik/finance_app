import logging
import sys

from app.config import LOG_LEVEL, LOGS_DIR


def setup_logging():
    """
    Настройка логирования для приложения.
    
    - В development: DEBUG уровень, цветной вывод в консоль
    - В production: INFO уровень, логи в файл
    """    
    log_dir = LOGS_DIR

    # Формат логов
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Очищаем старые хэндлеры (если есть)
    root_logger.handlers.clear()

    # ===== CONSOLE HANDLER (для разработки) =====
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # ===== FILE HANDLER (все логи) =====
    file_handler = logging.FileHandler(
        log_dir / "app.log",
        mode="a",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # ===== ERROR FILE HANDLER (только ошибки) =====
    error_handler = logging.FileHandler(
        log_dir / "errors.log",
        mode="a",
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(log_format, datefmt=date_format)
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)

    # Отключаем слишком болтливые библиотеки
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger