#!/usr/bin/env python3

import argparse
import logging
import pprint
import time

try:
    from pygments import highlight
    from pygments.lexers.python import PythonLexer
    from pygments.formatters.terminal256 import Terminal256Formatter
    PYGMENTS_INSTALLED = True
except ImportError:
    PYGMENTS_INSTALLED = False

from vkomment_utils import (VkWrapper, get_post_delay, get_target_time,
                            get_token_from_keyring, save_token_to_keyring,
                            STAW_CLUB_GROUP_ID, DEFAULT_TIME, GOLD_MEDAL_STR,
                            LOGGER)


def pp(obj):
    obj_str = pprint.pformat(obj)
    if PYGMENTS_INSTALLED:
        obj_str = highlight(obj_str, PythonLexer(), Terminal256Formatter())
    print(obj_str)


def wait_until_posted(post_at):
    delay = get_post_delay(post_at)
    h, m = divmod(delay // 60, 60)
    LOGGER.info("Waiting for %s", f'{h:.0f}:{m:0>2.0f}')
    time.sleep(delay)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Wait for new VK post in a group and post new comment ASAP")
    parser.add_argument('-t', '--token',
                        help="VK token (see https://devman.org/qna/63"
                             "/kak-poluchit-token-polzovatelja-dlja-vkontakte/ "
                             "for details)")
    parser.add_argument('-K', '--no-keyring', action='store_false', dest='use_keyring',
                        help="Do not use keyring for token management")
    parser.add_argument('-g', '--group-id', default=STAW_CLUB_GROUP_ID,
                        help=f"Group ID or alias (default is '{STAW_CLUB_GROUP_ID}')")
    parser.add_argument('-v', '--verbose', dest='verbosity', action='count',
                        default=0, help="Debug message verbosity")
    parser.add_argument('-G', '--github-workaround', dest='github_workaround',
                        action='store_true', default=False,
                        help="Replace empty strings with default values "
                             "(a workaround for GutHub Actions limitation)")
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('-T', '--posted-at', metavar='TIME', default=DEFAULT_TIME,
                            help=f"Expected time when the post appears (HH:MM in UTC, "
                                 f"default is '{DEFAULT_TIME}')")
    time_group.add_argument('-s', '--soon-and-sharp', action='store_true',
                            help="Wait for post at the closest 'HH:00' time "
                            "(e.g., expect post at 11:00 if script is run at 10:20")
    parser.add_argument('-l', '--local-time', action='store_true',
                        dest='is_time_local',
                        help="Interpret '--posted-at' as local time (not UTC)")
    comment_group = parser.add_mutually_exclusive_group()
    comment_group.add_argument('-p', '--plus', dest='comment_text',
                               action='store_const', const='+', default='+',
                               help="Comment with a plus sign (the default)")
    comment_group.add_argument('-d', '--double-plus', dest='comment_text',
                               action='store_const', const='++',
                               help="Comment with two plus signs (you and your friend)")
    comment_group.add_argument('-m', '--medal', dest='comment_text',
                               action='store_const', const=GOLD_MEDAL_STR,
                               help="Comment with a :1st_place_medal: emoji "
                                    "(for the cocky ones)")
    comment_group.add_argument('-c', '--comment-text', dest='comment_text',
                               help="Your own text to post as a comment")
    return parser.parse_args()


def get_token(args_):
    return args_.token or get_token_from_keyring()


def setup_logger(verb_arg=0):
    stderr_handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s]: %(message)s')
    stderr_handler.setFormatter(formatter)
    LOGGER.addHandler(stderr_handler)
    LOG_LEVELS = {0: logging.ERROR,
                  1: logging.INFO}
    log_level = LOG_LEVELS.get(verb_arg, logging.DEBUG)
    LOGGER.setLevel(log_level)


def fix_github_args(arg_namespace):
    """
    Replace empty strings with default values

    This is a workaround for GitHub action issue when specifying both manual
    and scheduled triggers (`on: [workflow_dispatch, schedule]`).
    See https://github.community/t/expressions-as-the-workflow-dispatch-input/141454
    """
    arg_namespace.group_id = arg_namespace.group_id or STAW_CLUB_GROUP_ID
    arg_namespace.posted_at = arg_namespace.posted_at or DEFAULT_TIME


def main(token, group_id, comment_text, post_at):
    vk = VkWrapper(token)
    group_id = vk.get_group_id(group_id)
    latest_id, post_time = vk.get_latest_post_and_time(group_id)
    LOGGER.info("Current latest post: %s from %s",
                f'https://vk.com/wall{group_id}_{latest_id}', post_time)
    wait_until_posted(post_at)
    LOGGER.info("The time has come, starting to wait for new post...")
    latest_id, _ = vk.get_latest_post_and_time(group_id, attempts=300)
    comment_id = vk.add_comment(group_id, latest_id, comment_text)
    LOGGER.info("Comment added: %s",
                f'https://vk.com/wall{group_id}_{latest_id}?reply={comment_id}')


if __name__ == '__main__':
    args = parse_args()
    if args.github_workaround:
        fix_github_args(args)
    setup_logger(args.verbosity)
    if args.token and args.use_keyring:
        save_token_to_keyring(args.token)
    post_incoming_at = get_target_time(args.posted_at, args.is_time_local,
                                       args.soon_and_sharp)
    LOGGER.info("Expecting new post at %s", post_incoming_at)
    main(get_token(args), args.group_id, args.comment_text, post_incoming_at)
