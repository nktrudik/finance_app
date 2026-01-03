import csv, logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

def parse_transactions_csv(file_path: str) -> List[Dict]:
    """
    Docstring для parse_transactions_csv
    
    :param file_path: Путь к csv файлу
    :type file_path: str
    :return: список транзакций из csv файла
    :rtype: List[Dict]
    """

    transactions = []
    skipped_rows = 0
    logger.info(f"📂 Начинаем парсинг CSV: {file_path}")

    with open(file=file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')

        try:
            for idx, row in enumerate(reader, start=1):
                # Пропускаем пустые строки
                if not row.get('Дата операции'):
                    logger.debug(f"В строке {idx}: пустая дата")
                    skipped_rows += 1
                    continue

                # Список поддерживаемых форматов
                date_formats = [
                    '%d.%m.%Y %H:%M:%S',  # 23.08.2023 14:22:27
                    '%d.%m.%Y',           # 23.08.2023
                    '%Y-%m-%d %H:%M:%S',  # 2023-08-23 14:22:27
                    '%Y-%m-%d',           # 2023-08-23
                ]
                
                # Парсим дату
                date_str = row['Дата операции'].strip()
                date = None
                for fmt in date_formats:
                    try:
                        date = datetime.strptime(date_str, fmt).date()
                        break 
                    except ValueError:
                        continue
                
                if date is None:
                    logger.warning(f"Строка {idx}: невалидная дата '{date_str}', пропускаем")
                    skipped_rows += 1
                    continue
                
                # Парсим сумму
                amount_str = row['Сумма операции'].replace(' ', '').replace(',', '.')
                try:
                    amount = float(amount_str)
                
                except ValueError:
                    logger.warning(f"Строка {idx}: невалидная сумма '{amount_str}', пропускаем")
                    skipped_rows += 1
                    continue

                # Парсим кэшбек
                cashback_str = row['Сумма операции'].replace(' ', '').replace(',', '.')
                try:
                    cashback = float(cashback_str) if cashback_str else 0.0
                
                except ValueError:
                    cashback = 0.0
                    logger.warning(f"Строка {idx}: невалидный кэшбек '{cashback_str}', ставим 0")

                # Формируем структуру
                transaction = {
                    'date': date.isoformat(),
                    'amount': abs(amount),
                    'category': row['Категория'].strip(),
                    'description': row['Описание'].strip(),
                    'mcc': row.get('MCC', '').strip(),
                    'cashback': cashback,
                    'is_expense': amount < 0,
                }

                transactions.append(transaction)
            
            logger.info(f"Парсинг завершён: {len(transactions)} транзакций загружено")
            if skipped_rows > 0:
                logger.warning(f"Пропущено {skipped_rows} строк с ошибками")
            
            return transactions
        
        except FileNotFoundError:
            logger.error(f"Файл не найден: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Ошибка парсинга CSV: {e}")
            raise


def format_transaction_text(transaction: Dict) -> str:
    """
    Docstring для format_transaction_text
    
    :param transaction: Принимает транзацию
    :type transaction: Dict
    :return: Возвращает текст с транзакцией для эмбэддингов
    :rtype: str
    
    """
    text = (
        f"{transaction['date']} "
        f"{transaction['category']} "
        f"{transaction['description']} "
        f"{transaction['amount']} руб"
    )
    
    if transaction.get('mcc'):
        text += f" MCC:{transaction['mcc']}"
    
    return text