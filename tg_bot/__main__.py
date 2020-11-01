import importlib
import re
import json
import requests
from typing import Optional, List
from parsel import Selector
from urllib.request import urlopen

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Unauthorized, BadRequest, TimedOut, NetworkError, ChatMigrated, TelegramError
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram.ext.dispatcher import run_async, DispatcherHandlerStop
from telegram.utils.helpers import escape_markdown

from tg_bot import dispatcher, updater, TOKEN, WEBHOOK, OWNER_ID, CERT_PATH, PORT, URL, LOGGER, \
    ALLOW_EXCL
# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from tg_bot.modules import ALL_MODULES
from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import is_user_admin
from tg_bot.modules.helper_funcs.misc import paginate_modules



PM_START_TEXT = """


┈┈┈┈╱▔▔▔▔╲┈┈┈┈
┈┈┈▕▕╲┊┊╱▏▏┈┈┈
┈┈┈▕▕▂╱╲▂▏▏┈┈┈
┈┈┈┈╲┊┊┊┊╱┈┈┈┈
┈┈┈┈▕╲▂▂╱▏┈┈┈┈
╱▔▔▔▔┊┊┊┊▔▔▔▔╲
HI 😉    {}, MY NAME IS {} !

I AM A PROBOT TO MAINTAIN YOUR GROUP 👸🏻

[THIS LEGEND](https://tg://user?id={}).

CREATED BY 🤴🏻[MY MASTER](https://t.me/saravanakrish)

HIT HELP FOR COMMANDS  /help



"""

HELP_STRINGS = """

Hello! my name *{}*.

*Main* commands available:
 - /start: start the bot
 - /help: PM's you this message.
 - /help <module name>: PM's you info about that module.
 - /settings:
   - in PM: will send you your settings for all supported modules.
   - in a group: will redirect you to pm, with all that chat's settings.


{}
And the following:
""".format(dispatcher.bot.first_name, "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n")


IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("tg_bot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(chat_id=chat_id,
                                text=text,
                                parse_mode=ParseMode.MARKDOWN,
                                reply_markup=keyboard)


@run_async
def test(bot: Bot, update: Update):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("This person edited a message")
    print(update.effective_message)

@run_async
def start(bot: Bot, update: Update, args: List[str]):
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower() == "disasters":
                IMPORTED["disasters"].send_disasters(update)
            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            update.effective_message.reply_text(
                PM_START_TEXT.format(escape_markdown(first_name), escape_markdown(bot.first_name), OWNER_ID),
                parse_mode=ParseMode.MARKDOWN, reply_markup= keyboard = [[InlineKeyboardButton(text="🤝Help",callback_data="help_back"),InlineKeyboardButton(text="🛡Creator🛡",url="https://t.me/saravanakrish")]]
    keyboard += [[InlineKeyboardButton(text="🌐Connect Group", callback_data="main_connect"),InlineKeyboardButton(text="⚜️Add Me⚜️",url="t.me/{}?startgroup=true".format(bot.username))]]
