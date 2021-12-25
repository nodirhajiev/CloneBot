#!/usr/bin/python3
# -*- coding: utf-8 -*-
import functools
import logging
import html
import os.path
import re
import sys

import traceback
from importlib import import_module
from logging import handlers
from pathlib import Path

from telegram import ParseMode
from telegram.ext import Updater, Dispatcher

import telegram.bot
from telegram.ext import messagequeue as mq
from telegram.ext.picklepersistence import PicklePersistence

from telegram.utils.helpers import mention_html
from telegram.utils.request import Request as TGRequest


from utils.config_loader import config


logger = logging.getLogger(__name__)


class MQBot(telegram.bot.Bot):
    """A subclass of Bot which delegates send method handling to MQ"""

    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or mq.MessageQueue(
            all_burst_limit=29,
            all_time_limit_ms=1017,
            group_burst_limit=19,
            group_time_limit_ms=60000,
        )

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass

    def auto_group(method):
        @functools.wraps(method)
        def wrapped(self, *args, **kwargs):
            chat_id = 0
            if "chat_id" in kwargs:
                chat_id = kwargs["chat_id"]
            elif len(args) > 0:
                chat_id = args[0]
            if type(chat_id) is str:
                is_group = True
            else:
                is_group = (chat_id < 0)
            return method(self, *args, **kwargs, isgroup=is_group)

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        """Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments"""
        return super(MQBot, self).send_message(*args, **kwargs)

    @mq.queuedmessage
    def send_photo(self, *args, **kwargs):
        """Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments"""
        return super(MQBot, self).send_photo(*args, **kwargs)
    #
    # @mq.queuedmessage
    # def edit_message_text(self, *args, **kwargs):
    #     '''Wrapped method would accept new `queued` and `isgroup`
    #     OPTIONAL arguments'''
    #     return super(MQBot, self).edit_message_text(*args, **kwargs)

    @mq.queuedmessage
    def forward_message(self, *args, **kwargs):
        """Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments"""
        return super(MQBot, self).forward_message(*args, **kwargs)
    #
    # @mq.queuedmessage
    # def answer_callback_query(self, *args, **kwargs):
    #     '''Wrapped method would accept new `queued` and `isgroup`
    #     OPTIONAL arguments'''
    #     return super(MQBot, self).answer_callback_query(*args, **kwargs)

    @mq.queuedmessage
    def leave_chat(self, *args, **kwargs):
        """Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments"""
        return super(MQBot, self).leave_chat(*args, **kwargs)


def main():
    log_file = init_logger()
    config.load_config()
    config.LOG_FILE = log_file

    telegram_pickle = PicklePersistence(filename='pickle_{}'.format(config.USER_IDS[0]),
                                        store_bot_data=True,
                                        store_user_data=True,
                                        store_chat_data=False)
    q = mq.MessageQueue()
    request = TGRequest(con_pool_size=8)
    my_bot = MQBot(config.TELEGRAM_TOKEN, request=request, mqueue=q)
    updater = Updater(bot=my_bot, use_context=True, persistence=telegram_pickle)

    updater.dispatcher.add_error_handler(error)

    load_handlers(updater.dispatcher)

    updater.start_polling()
    updater.bot.send_message(chat_id=config.USER_IDS[0], text='Welcome to ⚡️ CloneBot by Nodir X. Let\'s copy some data !')
    updater.idle()


def init_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    console_logger = logging.StreamHandler()
    console_logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_logger.setFormatter(formatter)
    root_logger.addHandler(console_logger)

    this_file_name = os.path.basename(os.path.splitext(os.path.basename(__file__))[0])

    Path('./logs/').mkdir(parents=True, exist_ok=True)
    logfile = './logs/' + this_file_name

    file_logger = handlers.TimedRotatingFileHandler(logfile, encoding='utf-8', when='midnight')
    file_logger.suffix = "%Y-%m-%d.log"
    file_logger.extMatch = re.compile(r'^\d{4}-\d{2}-\d{2}\.log$')
    file_logger.setLevel(logging.DEBUG)
    file_logger.setFormatter(formatter)
    root_logger.addHandler(file_logger)

    logging.getLogger('googleapiclient').setLevel(logging.CRITICAL)
    logging.getLogger('googleapiclient.discover').setLevel(logging.CRITICAL)
    logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.CRITICAL)
    logging.getLogger('google.auth.transport.requests').setLevel(logging.INFO)

    logging.getLogger('telegram.bot').setLevel(logging.INFO)
    logging.getLogger('telegram.ext.dispatcher').setLevel(logging.INFO)
    logging.getLogger('telegram.ext.updater').setLevel(logging.INFO)
    logging.getLogger('telegram.vendor.ptb_urllib3.urllib3.connectionpool').setLevel(logging.INFO)
    logging.getLogger('JobQueue').setLevel(logging.INFO)

    return logfile


def load_handlers(dispatcher: Dispatcher):
    """Load handlers from files in a 'bot' directory."""
    base_path = os.path.join(os.path.dirname(__file__), 'handlers')
    files = os.listdir(base_path)

    for file_name in files:
        if file_name.endswith('.py'):
            handler_module, _ = os.path.splitext(file_name)
            if handler_module == 'process_message':
                continue

            module = import_module(f'.{handler_module}', 'handlers')
            module.init(dispatcher)
            logger.info('loaded handler module: {}'.format(handler_module))
    module = import_module(f'.process_message', 'handlers')
    module.init(dispatcher)
    logger.info('loaded handler module: process_message')

if __name__ == '__main__':
    main()
