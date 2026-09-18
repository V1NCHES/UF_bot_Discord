# -*- coding: utf-8 -*-
import os
import json
import re
import sys

# Настройка UTF-8 для корректного вывода русских символов в консоли Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Пути к файлам
LOG_FILE = "выкочка.txt"
STATE_FILE = "state.json"
REPORT_FILE = "balances.txt"

def read_file_with_encodings(filepath):
    """Считывает файл, перебирая возможные кодировки."""
    encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'ansi']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Не удалось прочитать файл {filepath} ни в одной из стандартных кодировок.")

def parse_line(line):
    """Парсит строку лога, очищая её от кавычек и разделяя по табуляции."""
    # Разделяем по табуляции
    parts = line.strip().split('\t')
    if len(parts) < 4:
        # Если табуляции нет, попробуем разделить по пробелам, учитывая кавычки
        parts = re.findall(r'"([^"]*)"', line)
        if len(parts) < 4:
            return None
            
    # Убираем кавычки по краям, если они остались
    clean_parts = [p.strip('"') for p in parts]
    
    date = clean_parts[0]
    player = clean_parts[1]
    action = clean_parts[2]
    
    try:
        amount = int(clean_parts[3])
    except ValueError:
        try:
            amount = float(clean_parts[3])
        except ValueError:
            amount = 0
            
    return {
        "date": date,
        "player": player,
        "action": action,
        "amount": amount
    }

def load_state():
    """Загружает текущее состояние из state.json."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Предупреждение] Ошибка при чтении state.json: {e}. Начинаем с чистого листа.")
            
    return {
        "last_transaction": None,
        "balances": {}
    }

def save_state(state):
    """Сохраняет текущее состояние в state.json."""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[Ошибка] Не удалось сохранить state.json: {e}")

def create_table_string(balances):
    """Создает красивую текстовую таблицу с балансами."""
    sorted_balances = sorted(balances.items(), key=lambda item: item[1], reverse=True)
    
    # Заголовки
    col1_title = "Игрок"
    col2_title = "Текущий баланс"
    
    # Находим максимальную ширину колонок для правильного выравнивания
    col1_width = max(len(col1_title), max([len(player) for player, _ in sorted_balances] + [0])) + 2
    col2_width = max(len(col2_title), max([len(str(bal)) for _, bal in sorted_balances] + [0])) + 2
    
    border = f"+{'-' * col1_width}+{'-' * col2_width}+"
    header = f"| {col1_title:<{col1_width-2}} | {col2_title:<{col2_width-2}} |"
    
    lines = [border, header, border]
    for player, bal in sorted_balances:
        lines.append(f"| {player:<{col1_width-2}} | {bal:<{col2_width-2}} |")
    lines.append(border)
    
    return "\n".join(lines)

def main():
    print("=== Обработка логов гильдии ===")
    
    if not os.path.exists(LOG_FILE):
        print(f"[Ошибка] Файл логов '{LOG_FILE}' не найден в текущей папке.")
        return
        
    # 1. Загружаем состояние
    state = load_state()
    balances = state.get("balances", {})
    last_tx = state.get("last_transaction")
    
    # 2. Читаем файл логов
    try:
        content = read_file_with_encodings(LOG_FILE)
    except Exception as e:
        print(e)
        return
        
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    if not lines:
        print("[Предупреждение] Файл логов пуст.")
        return
        
    # Парсим все транзакции из файла
    all_transactions = []
    # Пропускаем заголовок (первая строка, если там есть слово "Дата" или "Игрок")
    start_idx = 1 if "Дата" in lines[0] or "Игрок" in lines[0] else 0
    
    for line in lines[start_idx:]:
        tx = parse_line(line)
        if tx:
            all_transactions.append(tx)
            
    if not all_transactions:
        print("[Предупреждение] Не удалось распознать ни одной транзакции в файле.")
        return
        
    # 3. Определяем новые транзакции
    # Лог идет сверху вниз от новых к старым (all_transactions[0] - самая новая).
    # Ищем, где находится последняя обработанная транзакция (last_tx)
    new_transactions = []
    
    if last_tx:
        found_idx = -1
        for idx, tx in enumerate(all_transactions):
            # Сравниваем транзакции по всем ключевым полям для надежности
            if (tx["date"] == last_tx.get("date") and 
                tx["player"] == last_tx.get("player") and 
                tx["action"] == last_tx.get("action") and 
                tx["amount"] == last_tx.get("amount")):
                found_idx = idx
                break
                
        if found_idx != -1:
            # Нашли последнее обработанное действие.
            # Все действия с индексом меньше found_idx являются новыми (так как файл отсортирован по убыванию даты).
            new_transactions = all_transactions[:found_idx]
            print(f"Найдено последнее обработанное действие от {last_tx['date']} (Игрок: {last_tx['player']}).")
            print(f"Количество новых действий для обработки: {len(new_transactions)}.")
        else:
            # Если последняя транзакция не найдена в файле, обрабатываем весь файл целиком
            print("[Предупреждение] Последнее действие не найдено в файле (возможно, лог был очищен или заменен).")
            print("Обрабатываем весь файл с нуля.")
            new_transactions = all_transactions
    else:
        print("Первый запуск. Обрабатываем весь файл целиком.")
        new_transactions = all_transactions
        
    # 4. Обрабатываем новые транзакции в хронологическом порядке (снизу вверх)
    if new_transactions:
        # Разворачиваем список новых транзакций, чтобы идти от старых к новым
        for tx in reversed(new_transactions):
            player = tx["player"]
            amount = tx["amount"]
            # Обновляем баланс игрока
            balances[player] = balances.get(player, 0) + amount
            
        # Обновляем последнее обработанное действие (самое первое в исходном файле среди новых, то есть new_transactions[0])
        state["last_transaction"] = new_transactions[0]
        print("[Успешно] Балансы обновлены новыми данными.")
    else:
        print("Новых действий не найдено. Балансы актуальны.")
        
    # Обновляем балансы в стейте
    state["balances"] = balances
    
    # 5. Сохраняем состояние
    save_state(state)
    
    # 6. Генерируем отчет
    table_str = create_table_string(balances)
    
    # Выводим в консоль
    print("\n" + table_str + "\n")
    
    # Записываем отчет в файл balances.txt
    try:
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write("=== ТЕКУЩИЕ БАЛАНСЫ ИГРОКОВ (ВЫКАЧКА) ===\n\n")
            f.write(table_str)
            f.write("\n\nПоследнее обработанное действие:\n")
            if state["last_transaction"]:
                f.write(f"Дата: {state['last_transaction']['date']}\n")
                f.write(f"Игрок: {state['last_transaction']['player']}\n")
                f.write(f"Действие: {state['last_transaction']['action']}\n")
                f.write(f"Сумма: {state['last_transaction']['amount']}\n")
            else:
                f.write("Нет данных\n")
        print(f"Отчет успешно сохранен в файл '{REPORT_FILE}'.")
    except Exception as e:
        print(f"[Ошибка] Не удалось сохранить отчет: {e}")

if __name__ == "__main__":
    main()
