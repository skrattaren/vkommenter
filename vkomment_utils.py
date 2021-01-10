import datetime
import json
import sys
import time

import keyring
import requests


UTC = datetime.timezone.utc

GOLD_MEDAL_STR = '\U0001F947'
STAW_CLUB_GROUP_ID = 'stawclub'
DEFAULT_TIME = '06:00'

_KEYRING_SERVICE = 'VK'
_KEYRING_TOKEN_NAME = 'vkomment_token'


def get_token_from_keyring():
    return keyring.get_password(_KEYRING_SERVICE, _KEYRING_TOKEN_NAME)


class VkWrapper():
    API_VERSION = '5.125'
    API_URL_STUB = 'https://api.vk.com/method/{method}'

    token = None
    basic_params = {'v': API_VERSION}

    def __init__(self, token):
        self.basic_params['access_token'] = token

    def send_api_request(self, method, params):
        payload = {}
        payload.update(self.basic_params)
        payload.update(params)
        response = requests.get(self.API_URL_STUB.format(method=method),
                                params=payload)
        # print(response.url)
        return json.loads(response.text)

    def get_group_id(self, name_or_id):
        response = self.send_api_request('groups.getById',
                                         {'group_id': name_or_id})
        if response.get('error') is not None:
            print(f"Couldn't find a group with name or id {name_or_id}",
                  file=sys.stderr)
            sys.exit(1)
        return "-{}".format(response['response'][0]['id'])

    def get_latest_post(self, group_id, attempt=60):
        if attempt < 0:
            print("Didn't find any suitable post!", file=sys.stderr)
            sys.exit(1)
        data = self.send_api_request('wall.get',
                                     {'owner_id': group_id,
                                      'offset': 0,
                                      'count': 1,
                                      'filter': 'owner'})
        latest = data['response']['items'][0]
        now = time.time()
        # print("Found post from {} (now is {})"
        #       "".format(datetime.datetime.fromtimestamp(latest['date']),
        #                 datetime.datetime.fromtimestamp(now)))
        if now - latest['date'] > 666:
            time.sleep(1)
            return self.get_latest_post(group_id, attempt - 1)
        return latest['id']

    def add_comment(self, group_id, post_id, comment_text):
        data = self.send_api_request('wall.createComment',
                                     {'post_id': post_id,
                                      'owner_id': group_id,
                                      'message': comment_text})
        return data

def get_target_time(post_incoming_at):
    post_incoming_at = [int(d) for d in post_incoming_at.split(':')]
    today = datetime.datetime.now(tz=UTC).date()
    post_at = datetime.datetime(today.year, today.month, today.day,
                                post_incoming_at[0], post_incoming_at[1], 0,
                                tzinfo=UTC)
    if post_at < datetime.datetime.now(tz=UTC):
        post_at += datetime.timedelta(days=1)
    return post_at
