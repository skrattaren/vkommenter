#!/usr/bin/env python3

import argparse
import datetime
import random
import sys
import traceback

from vkomment_utils import VkWrapper

RANDOM_ID = random.randint(2 ** 16, 2 ** 32)

# pylint: disable=redefined-outer-name
def main(args):
    vk_bot = VkWrapper(args.bot_key)
    if args.include_time:
        utcnow = datetime.datetime.utcnow().strftime('%H:%M:%S +00:00, %d %b %Y')
        message = "{} (at {})".format(args.message_text, utcnow)
    else:
        message = args.message_text
    vk_bot.send_api_request('messages.send',
                            {'user_id': args.user_id,
                             'random_id': RANDOM_ID,
                             'message': message})

def parse_args():
    parser = argparse.ArgumentParser(
        description="Send a message via VK")
    parser.add_argument('-k', '--bot-key',
                        help="Chat bot's key, see https://vk.com/dev/bots_docs")
    # TODO: actually implement keyring
    parser.add_argument('-K', '--no-keyring', action='store_false', dest='use_keyring',
                        help="Do not use keyring for token management")
    parser.add_argument('-u', '--user-id', required=True,
                        help="Send message to this user")
    parser.add_argument('-T', '--include-time', action='store_true',
                        help="Add timestamp to message")
    parser.add_argument('-0', '--always-success', action='store_true',
                        help="Always exit successfully (exit code 0)")
    parser.add_argument('message_text')
    return parser.parse_args()

if __name__ == '__main__':
    # guard against anything and everything
    try:
        args = parse_args()
        main(args)
    except Exception as err:
        traceback.print_tb(err.__traceback__)
        if not args.always_success:
            sys.exit(1)
