#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram-бот для управления задачами с приоритетами и напоминаниями
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы для ConversationHandler
CHOOSING_ACTION, ADD_TASK, SET_PRIORITY, SET_REMINDER = range(4)

# Приоритеты задач
PRIORITIES = ['🔴 Высокий', '🟡 Средний', '🟢 Низкий']

# Файл для хранения данных
DATA_FILE = 'tasks_data.json'


class TaskManager:
    """Класс для управления задачами"""
    
    def __init__(self, data_file: str = DATA_FILE):
        self.data_file = data_file
        self.tasks: Dict[int, Dict] = self._load_tasks()
    
    def _load_tasks(self) -> Dict[int, Dict]:
        """Загрузка задач из файла"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Конвертируем ключи обратно в int
                    return {int(k): v for k, v in data.items()}
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            return {}
    
    def _save_tasks(self):
        """Сохранение задач в файл"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
    
    def get_user_tasks(self, user_id: int) -> List[Dict]:
        """Получение задач пользователя"""
        if user_id not in self.tasks:
            self.tasks[user_id] = {'tasks': []}
        return self.tasks[user_id]['tasks']
    
    def add_task(self, user_id: int, text: str, priority: str = '🟡 Средний', 
                 reminder: str = None):
        """Добавление новой задачи"""
        if user_id not in self.tasks:
            self.tasks[user_id] = {'tasks': []}
        
        task = {
            'id': len(self.tasks[user_id]['tasks']) + 1,
            'text': text,
            'priority': priority,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'completed': False,
            'reminder': reminder
        }
        
        self.tasks[user_id]['tasks'].append(task)
        self._save_tasks()
        return task
    
    def complete_task(self, user_id: int, task_id: int) -> bool:
        """Отметка задачи как выполненной"""
        tasks = self.get_user_tasks(user_id)
        for task in tasks:
            if task['id'] == task_id:
                task['completed'] = True
                self._save_tasks()
                return True
        return False
    
    def delete_task(self, user_id: int, task_id: int) -> bool:
        """Удаление задачи"""
        tasks = self.get_user_tasks(user_id)
        initial_length = len(tasks)
        self.tasks[user_id]['tasks'] = [t for t in tasks if t['id'] != task_id]
        
        if len(self.tasks[user_id]['tasks']) < initial_length:
            self._save_tasks()
            return True
        return False
    
    def get_tasks_by_priority(self, user_id: int) -> Dict[str, List]:
        """Получение задач, отсортированных по приоритету"""
        tasks = self.get_user_tasks(user_id)
        categorized = {p: [] for p in PRIORITIES}
        
        for task in tasks:
            if not task['completed']:
                priority = task.get('priority', '🟡 Средний')
                if priority in categorized:
                    categorized[priority].append(task)
        
        return categorized


# Инициализация менеджера задач
task_manager = TaskManager()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Приветственное сообщение и главное меню"""
    user = update.effective_user
    
    welcome_message = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я бот для управления задачами. Я помогу тебе:\n"
        f"📝 Создавать задачи\n"
        f"🎯 Организовывать их по приоритетам\n"
        f"⏰ Устанавливать напоминания\n"
        f"✅ Отслеживать выполнение\n\n"
        f"Используй команды:\n"
        f"/add - Добавить новую задачу\n"
        f"/list - Показать все задачи\n"
        f"/complete - Отметить задачу выполненной\n"
        f"/delete - Удалить задачу\n"
        f"/help - Помощь\n"
        f"/cancel - Отменить текущее действие"
    )
    
    await update.message.reply_text(welcome_message)
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам"""
    help_text = (
        "📚 *Доступные команды:*\n\n"
        "/start - Начать работу сботом\n"
        "/add - Добавить новую задачу\n"
        "/list - Показать список задач\n"
        "/complete - Отметить задачу как выполненную\n"
        "/delete - Удалить задачу\n"
        "/help - Показать эту справку\n"
        "/cancel - Отменить текущее действие\n\n"
        "*Приоритеты задач:*\n"
        "🔴 Высокий - Срочные и важные задачи\n"
        "🟡 Средний - Обычные задачи\n"
        "🟢 Низкий - Задачи с низким приоритетом"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса добавления задачи"""
    await update.message.reply_text(
        "📝 Введите описание задачи:\n"
        "(или /cancel для отмены)"
    )
    return ADD_TASK


async def add_task_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение текста задачи и запрос приоритета"""
    context.user_data['task_text'] = update.message.text
    
    # Клавиатура с приоритетами
    keyboard = [[priority] for priority in PRIORITIES]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎯 Выберите приоритет задачи:",
        reply_markup=reply_markup
    )
    return SET_PRIORITY


async def set_priority(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Установка приоритета и запрос напоминания"""
    priority = update.message.text
    
    if priority not in PRIORITIES:
        await update.message.reply_text("❌ Пожалуйста, выберите приоритет из списка")
        return SET_PRIORITY
    
    context.user_data['task_priority'] = priority
    
    # Клавиатура для напоминаний
    keyboard = [
        ['Через 1 час', 'Через 3 часа'],
        ['Завтра', 'Через неделю'],
        ['Без напоминания']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "⏰ Когда напомнить о задаче?",
        reply_markup=reply_markup
    )
    return SET_REMINDER


async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Установка напоминания и сохранение задачи"""
    reminder_text = update.message.text
    user_id = update.effective_user.id
    
    # Вычисляем время напоминания
    reminder_time = None
    if reminder_text == 'Через 1 час':
        reminder_time = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    elif reminder_text == 'Через 3 часа':
        reminder_time = (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
    elif reminder_text == 'Завтра':
        reminder_time = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    elif reminder_text == 'Через неделю':
        reminder_time = (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Создаем задачу
    task = task_manager.add_task(
        user_id=user_id,
        text=context.user_data['task_text'],
        priority=context.user_data['task_priority'],
        reminder=reminder_time
    )
    
    # Формируем сообщение о созданной задаче
    message = (
        f"✅ Задача создана!\n\n"
        f"📝 {task['text']}\n"
        f"🎯 Приоритет: {task['priority']}\n"
        f"📅 Создана: {task['created_at']}\n"
    )
    
    if reminder_time:
        message += f"⏰ Напоминание: {reminder_time}"
    
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    
    # Очищаем временные данные
    context.user_data.clear()
    
    return ConversationHandler.END


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список задач"""
    user_id = update.effective_user.id
    tasks_by_priority = task_manager.get_tasks_by_priority(user_id)
    
    # Проверяем, есть ли активные задачи
    total_tasks = sum(len(tasks) for tasks in tasks_by_priority.values())
    
    if total_tasks == 0:
        await update.message.reply_text(
            "📭 У вас пока нет активных задач.\n"
            "Используйте /add чтобы добавить новую задачу!"
        )
        return
    
    # Формируем список задач по приоритетам
    message = "📋 *Ваши задачи:*\n\n"
    
    for priority in PRIORITIES:
        tasks = tasks_by_priority[priority]
        if tasks:
            message += f"*{priority}*\n"
            for task in tasks:
                status = "✅" if task['completed'] else "⏹"
                message += f"{status} #{task['id']}: {task['text']}\n"
                if task.get('reminder'):
                    message += f"   ⏰ Напоминание: {task['reminder']}\n"
            message += "\n"
    
    # Показываем выполненные задачи
    all_tasks = task_manager.get_user_tasks(user_id)
    completed_tasks = [t for t in all_tasks if t['completed']]
    
    if completed_tasks:
        message += "*✅ Выполненные:*\n"
        for task in completed_tasks[-5:]:  # Показываем последние 5
            message += f"✅ #{task['id']}: {task['text']}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отметить задачу как выполненную"""
    user_id = update.effective_user.id
    tasks = task_manager.get_user_tasks(user_id)
    active_tasks = [t for t in tasks if not t['completed']]
    
    if not active_tasks:
        await update.message.reply_text(
            "📭 У вас нет активных задач для завершения."
        )
        return
    
    # Показываем список активных задач
    message = "Выберите номер задачи для завершения:\n\n"
    for task in active_tasks:
        message += f"#{task['id']}: {task['text']} ({task['priority']})\n"
    
    await update.message.reply_text(message)
    await update.message.reply_text(
        "Отправьте номер задачи (например: 1) или /cancel для отмены"
    )
    
    # Сохраняем контекст для следующего сообщения
    context.user_data['awaiting_complete'] = True


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить задачу"""
    user_id = update.effective_user.id
    tasks = task_manager.get_user_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text(
            "📭 У вас нет задач для удаления."
        )
        return
    
    # Показываем список всех задач
    message = "Выберите номер задачи для удаления:\n\n"
    for task in tasks:
        status = "✅" if task['completed'] else "⏹"
        message += f"{status} #{task['id']}: {task['text']} ({task['priority']})\n"
    
    await update.message.reply_text(message)
    await update.message.reply_text(
        "Отправьте номер задачи (например: 1) или /cancel для отмены"
    )
    
    # Сохраняем контекст для следующего сообщения
    context.user_data['awaiting_delete'] = True


async def handle_task_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий с задачами (завершение/удаление)"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Проверяем, что пользователь ввел число
    try:
        task_id = int(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректный номер задачи."
        )
        return
    
    # Обработка завершения задачи
    if context.user_data.get('awaiting_complete'):
        if task_manager.complete_task(user_id, task_id):
            await update.message.reply_text(
                f"✅ Задача #{task_id} отмечена как выполненная!"
            )
        else:
            await update.message.reply_text(
                f"❌ Задача #{task_id} не найдена."
            )
        context.user_data.pop('awaiting_complete', None)
    
    # Обработка удаления задачи
    elif context.user_data.get('awaiting_delete'):
        if task_manager.delete_task(user_id, task_id):
            await update.message.reply_text(
                f"🗑 Задача #{task_id} удалена!"
            )
        else:
            await update.message.reply_text(
                f"❌ Задача #{task_id} не найдена."
            )
        context.user_data.pop('awaiting_delete', None)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Действие отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "😔 Произошла ошибка при обработке запроса. "
                "Пожалуйста, попробуйте еще раз или обратитесь к /help"
            )
    except Exception as e:
        logger.error(f"Error in error_handler: {e}")


def main():
    """Запуск бота"""
    # Получаем токен из переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        print("❌ Ошибка: Не найден TELEGRAM_BOT_TOKEN")
        print("Пожалуйста, создайте файл .env и добавьте туда токен бота")
        return
    
    # Создаем приложение
    application = Application.builder().token(token).build()
    
    # ConversationHandler для добавления задачи
    add_task_conv = ConversationHandler(
        entry_points=[CommandHandler('add', add_task_start)],
        states={
            ADD_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_text)],
            SET_PRIORITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_priority)],
            SET_REMINDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_reminder)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(add_task_conv)
    application.add_handler(CommandHandler('list', list_tasks))
    application.add_handler(CommandHandler('complete', complete_task))
    application.add_handler(CommandHandler('delete', delete_task))
    application.add_handler(CommandHandler('cancel', cancel))
    
    # Обработчик текстовых сообщений для действий с задачами
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_action)
    )
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("🤖 Бот запущен!")
    print("🤖 Бот успешно запущен!")
    print("Нажмите Ctrl+C для остановки")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

