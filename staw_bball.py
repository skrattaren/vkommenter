#!/usr/bin/env python3

import argparse
import datetime
import pprint
import time

try:
    from pygments import highlight
    from pygments.lexers.python import PythonLexer
    from pygments.formatters.terminal256 import Terminal256Formatter
    PYGMENTS_INSTALLED = True
except ImportError:
    PYGMENTS_INSTALLED = False

from vkomment_utils import (VkWrapper, get_target_time, get_token_from_keyring,
                            UTC, STAW_CLUB_GROUP_ID, DEFAULT_TIME, GOLD_MEDAL_STR)

def pp(obj):
    obj_str = pprint.pformat(obj)
    if PYGMENTS_INSTALLED:
        obj_str = highlight(obj_str, PythonLexer(), Terminal256Formatter())
    print(obj_str)

def wait_until_posted(post_at):
    delay = (post_at - datetime.datetime.now(tz=UTC)).total_seconds()
    h, m = divmod(delay // 60, 60)
    print(f"Waiting for {h:.0f}:{m:0>2.0f}")
    time.sleep(delay)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Wait for new VK post in a group and post new comment ASAP")
    parser.add_argument('-t', '--token',
                        help="VK token (see https://devman.org/qna/63"
                             "/kak-poluchit-token-polzovatelja-dlja-vkontakte/ "
                             "for details)")
    parser.add_argument('-K', '--no-keyring', action='store_true',
                        help="Do not use keyring for token management")
    parser.add_argument('-g', '--group-id', default=STAW_CLUB_GROUP_ID,
                        help=f"Group ID or alias (default is '{STAW_CLUB_GROUP_ID}')")
    parser.add_argument('-T', '--posted-at', metavar='TIME', default=DEFAULT_TIME,
                        help=f"Expected time when the post appears (HH:MM in UTC, "
                             f"default is '{DEFAULT_TIME}')")
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
    return parser.parse_args()

def get_token(args_):
    return args_.token or get_token_from_keyring()

def main(token, group_id, comment_text, post_at):
    vk = VkWrapper(token)
    group_id = vk.get_group_id(group_id)
    wait_until_posted(post_at)
    latest_id = vk.get_latest_post(group_id)
    pp(vk.add_comment(group_id, latest_id, comment_text))


if __name__ == '__main__':
    args = parse_args()
    post_incoming_at = get_target_time(args.posted_at)
    main(get_token(args), args.group_id, args.comment_text, post_incoming_at)
