import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from telegram import Update, CallbackQuery, Message, User, Chat
from telegram.ext import CallbackContext

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.callbacks import (
    show_comments,
    comment_page,
    get_recipe_title,
    comment_pagination_handler,
    button_callback,
    comment_entry_handler,
    handle_rating_input
)

class TestCommentsFunctions(unittest.TestCase):
    def setUp(self):
        self.user = User(id=123, first_name="Test", is_bot=False)
        self.chat = Chat(id=456, type='private')
        self.message = Message(message_id=789, date=None, chat=self.chat)
        self.callback_query = CallbackQuery(id="123", from_user=self.user, chat_instance="test", data="test_data")
        self.update = Update(update_id=1, callback_query=self.callback_query)
        self.update.callback_query.message = self.message
        self.context = MagicMock(spec=CallbackContext)
        self.context.user_data = {}
        self.context.bot_data = {"db_conn": MagicMock()}
        self.cursor = MagicMock()
        self.context.bot_data["db_conn"].cursor.return_value = self.cursor

    def test_show_comments(self):
        self.update.callback_query.data = "view_comments_42"
        with patch('your_module.comment_page') as mock_comment_page:
            show_comments(self.update, self.context)
            self.assertEqual(self.context.user_data["comments_recipe_id"], 42)
            self.assertEqual(self.context.user_data["comments_page"], 0)
            mock_comment_page.assert_called_once_with(self.update, self.context)

    def test_comment_page_no_comments(self):
        self.context.user_data["comments_recipe_id"] = 42
        self.cursor.fetchall.return_value = []
        comment_page(self.update, self.context)
        self.update.callback_query.edit_message_text.assert_called_once_with("Нет комментариев к этому рецепту.")

    def test_comment_page_with_comments(self):
        self.context.user_data["comments_recipe_id"] = 42
        self.context.user_data["selected_index"] = 0
        self.context.user_data["lang"] = "en"
        self.cursor.fetchall.return_value = [
            ("Test comment", "test_user", "2023-01-01 00:00:00")
        ]
        with patch('your_module.get_recipe_title', return_value="Test Recipe"):
            comment_page(self.update, self.context)
            expected_text = (
                'Комментарии к рецепту "Test Recipe"\n\n'
                'Комментарий:\nTest comment\n\n'
                'Пользователь: test_user\n'
                'Дата: 01/01/2023'
            )
            self.update.callback_query.edit_message_text.assert_called_once()
            args, kwargs = self.update.callback_query.edit_message_text.call_args
            self.assertIn(expected_text, kwargs['text'])
            self.assertIsNotNone(kwargs['reply_markup'])

    def test_get_recipe_title_en(self):
        self.cursor.fetchone.return_value = ("Test Recipe",)
        result = get_recipe_title(42, self.cursor, "en")
        self.assertEqual(result, "Test Recipe")

    def test_get_recipe_title_ru(self):
        self.cursor.fetchone.return_value = ("Test Recipe",)
        with patch('your_module.translate_to_ru', return_value="Тестовый рецепт"):
            result = get_recipe_title(42, self.cursor, "ru")
            self.assertEqual(result, "Тестовый рецепт")

    def test_comment_pagination_handler_prev(self):
        self.update.callback_query.data = "comment_prev"
        self.context.user_data["comments_page"] = 1
        with patch('your_module.comment_page') as mock_comment_page:
            comment_pagination_handler(self.update, self.context)
            self.assertEqual(self.context.user_data["comments_page"], 0)
            mock_comment_page.assert_called_once_with(self.update, self.context)

    def test_comment_pagination_handler_next(self):
        self.update.callback_query.data = "comment_next"
        self.context.user_data["comments_page"] = 0
        with patch('your_module.comment_page') as mock_comment_page:
            comment_pagination_handler(self.update, self.context)
            self.assertEqual(self.context.user_data["comments_page"], 1)
            mock_comment_page.assert_called_once_with(self.update, self.context)

class TestButtonCallback(unittest.TestCase):
    def setUp(self):
        self.user = User(id=123, first_name="Test", is_bot=False)
        self.chat = Chat(id=456, type='private')
        self.message = Message(message_id=789, date=None, chat=self.chat)
        self.callback_query = CallbackQuery(id="123", from_user=self.user, chat_instance="test", data="test_data")
        self.update = Update(update_id=1, callback_query=self.callback_query)
        self.update.callback_query.message = self.message
        self.context = MagicMock(spec=CallbackContext)
        self.context.user_data = {}
        self.context.bot_data = {"db_conn": MagicMock()}
        self.cursor = MagicMock()
        self.context.bot_data["db_conn"].cursor.return_value = self.cursor

    def test_button_callback_back(self):
        self.update.callback_query.data = "back"
        button_callback(self.update, self.context)
        self.update.callback_query.edit_message_text.assert_called_once()
        args, kwargs = self.update.callback_query.edit_message_text.call_args
        self.assertIn("Добро пожаловать в Treat's Searcher!", kwargs['text'])
        self.assertIsNotNone(kwargs['reply_markup'])

    def test_button_callback_search(self):
        self.update.callback_query.data = "search"
        button_callback(self.update, self.context)
        self.update.callback_query.edit_message_text.assert_called_once_with(
            "Выбери язык поиска:",
            reply_markup=unittest.mock.ANY
        )

    def test_button_callback_lang_ru(self):
        self.update.callback_query.data = "lang_ru"
        button_callback(self.update, self.context)
        self.assertEqual(self.context.user_data["lang"], "ru")
        self.update.callback_query.edit_message_text.assert_called_once_with(
            "Как ты хочешь найти рецепт?",
            reply_markup=unittest.mock.ANY
        )

    def test_button_callback_select_recipe(self):
        self.update.callback_query.data = "select_1"
        self.context.user_data["search_results"] = [42]
        self.cursor.fetchone.return_value = ("Test Recipe",)
        button_callback(self.update, self.context)
        self.assertEqual(self.context.user_data["selected_recipe_id"], 42)
        self.assertEqual(self.context.user_data["selected_index"], 0)
        self.update.callback_query.edit_message_text.assert_called_once_with(
            'Вы выбрали рецепт: "Test Recipe"\nЧто вы хотите узнать?',
            reply_markup=unittest.mock.ANY
        )

    def test_button_callback_recipe_ingredients(self):
        self.update.callback_query.data = "recipe_ingredients"
        self.context.user_data["selected_recipe_id"] = 42
        self.context.user_data["selected_index"] = 0
        self.cursor.fetchone.return_value = ("['ing1', 'ing2']",)
        button_callback(self.update, self.context)
        self.update.callback_query.edit_message_text.assert_called_once_with(
            "🥕 Ингредиенты:\ning1, ing2",
            reply_markup=unittest.mock.ANY
        )

    def test_button_callback_recipe_steps(self):
        self.update.callback_query.data = "recipe_steps"
        self.context.user_data["selected_recipe_id"] = 42
        self.context.user_data["selected_index"] = 0
        self.cursor.fetchone.return_value = ("['step1', 'step2']",)
        button_callback(self.update, self.context)
        self.update.callback_query.edit_message_text.assert_called_once()
        args, kwargs = self.update.callback_query.edit_message_text.call_args
        self.assertIn("1. step1\n2. step2", kwargs['text'])

    def test_button_callback_view_comments(self):
        self.update.callback_query.data = "view_comments_42"
        with patch('your_module.comment_page') as mock_comment_page:
            button_callback(self.update, self.context)
            self.assertEqual(self.context.user_data["comments_recipe_id"], 42)
            self.assertEqual(self.context.user_data["comments_page"], 0)
            mock_comment_page.assert_called_once_with(self.update, self.context)

    def test_button_callback_rate_recipe(self):
        self.update.callback_query.data = "rate_recipe_42"
        button_callback(self.update, self.context)
        self.assertEqual(self.context.user_data["rating_recipe_id"], 42)
        self.assertTrue(self.context.user_data["awaiting_rating"])
        self.update.callback_query.message.reply_text.assert_called_once_with("Поставьте оценку от 1 до 5:")

class TestCommentAndRatingHandlers(unittest.TestCase):
    def setUp(self):
        self.user = User(id=123, first_name="Test", is_bot=False)
        self.chat = Chat(id=456, type='private')
        self.message = Message(message_id=789, date=None, chat=self.chat, from_user=self.user)
        self.update = Update(update_id=1, message=self.message)
        self.context = MagicMock(spec=CallbackContext)
        self.context.user_data = {}
        self.context.bot_data = {"db_conn": MagicMock()}

    def test_comment_entry_handler(self):
        self.update.callback_query = CallbackQuery(id="123", from_user=self.user, chat_instance="test", data="comment_42")
        comment_entry_handler(self.update, self.context)
        self.assertEqual(self.context.user_data["comment_recipe_id"], 42)
        self.assertTrue(self.context.user_data["awaiting_comment"])
        self.update.callback_query.message.reply_text.assert_called_once_with("Напиши комментарий к рецепту:")

    def test_handle_rating_input_valid(self):
        self.context.user_data["awaiting_rating"] = True
        self.context.user_data["rating_recipe_id"] = 42
        self.context.user_data["selected_index"] = 0
        self.update.message.text = "5"
        handle_rating_input(self.update, self.context)
        self.context.bot_data["db_conn"].cursor().execute.assert_called()
        self.context.bot_data["db_conn"].commit.assert_called_once()
        self.assertNotIn("awaiting_rating", self.context.user_data)
        self.assertNotIn("rating_recipe_id", self.context.user_data)
        self.update.message.reply_text.assert_called_once_with(
            "Спасибо за вашу оценку! ⭐",
            reply_markup=unittest.mock.ANY
        )

    def test_handle_rating_input_invalid(self):
        self.context.user_data["awaiting_rating"] = True
        self.update.message.text = "6"
        handle_rating_input(self.update, self.context)
        self.update.message.reply_text.assert_called_once_with("Пожалуйста, введите число от 1 до 5.")

if __name__ == '__main__':
    unittest.main()