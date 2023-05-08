import datetime
import json
import logging
import sys
import time

try:
    import keyring
except ImportError:
    keyring = None
import requests


LOGGER = logging.getLogger('vkomment')

UTC = datetime.timezone.utc

GOLD_MEDAL_STR = '\U0001F947'
STAW_CLUB_GROUP_ID = 'stawclub'
DEFAULT_TIME = '06:00'

_KEYRING_SERVICE = 'VK'
_KEYRING_TOKEN_NAME = 'vkomment_token'


class VkError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self, message)


def get_token_from_keyring():
    if keyring is None:
        LOGGER.error("Cannot find `keyring` module")
        sys.exit(1)
    return keyring.get_password(_KEYRING_SERVICE, _KEYRING_TOKEN_NAME)


def save_token_to_keyring(token):
    if keyring is None:
        LOGGER.warning("Cannot find `keyring` module, token won't be saved")
        return
    keyring.set_password(_KEYRING_SERVICE, _KEYRING_TOKEN_NAME, token)


def get_local_tz():
    return datetime.datetime.now(tz=UTC).astimezone().tzinfo


def get_timezone(is_time_local):
    return get_local_tz() if is_time_local else UTC


def get_post_delay(post_at):
    return (post_at - datetime.datetime.now(tz=UTC)).total_seconds()


def get_target_time(post_incoming_at, is_time_local=False, soon_and_sharp=False):
    tz = get_timezone(is_time_local)
    if soon_and_sharp:
        post_at = datetime.datetime.now(tz=UTC) + datetime.timedelta(hours=1)
        post_at = post_at.replace(minute=0, second=0, microsecond=0)
        return post_at
    try:
        post_incoming_at = [int(d) for d in post_incoming_at.split(':')]
    except ValueError:
        LOGGER.error("Invalid time provided: %s", post_incoming_at)
        sys.exit(1)
    today = datetime.datetime.now(tz=tz).date()
    post_at = datetime.datetime(today.year, today.month, today.day,
                                post_incoming_at[0], post_incoming_at[1], 0,
                                tzinfo=tz)
    if post_at < datetime.datetime.now(tz=tz):
        post_at += datetime.timedelta(days=1)
    return post_at


class VkWrapper():
    API_VERSION = '5.131'
    API_URL_STUB = 'https://api.vk.com/method/{method}'

    basic_params = {'v': API_VERSION}

    def __init__(self, token):
        self.basic_params['access_token'] = token

    def send_api_request(self, method, params):
        payload = {}
        payload.update(self.basic_params)
        payload.update(params)
        response = requests.get(self.API_URL_STUB.format(method=method),
                                params=payload, timeout=3)
        r_text = json.loads(response.text)
        vk_error = r_text.get('error')
        if vk_error is not None:
            raise VkError(vk_error)
        return r_text

    def get_group_id(self, name_or_id):
        try:
            response = self.send_api_request('groups.getById',
                                             {'group_id': name_or_id})
        except VkError as e:
            LOGGER.error("Couldn't find a group with name or id %s, error:\n%s",
                         name_or_id, e.message)
            sys.exit(1)
        return "-{}".format(response['response'][0]['id'])

    def get_latest_post_and_time(self, group_id, attempts=None):
        if attempts is not None and attempts < 0:
            LOGGER.error("Didn't find any suitable post!")
            sys.exit(1)
        data = self.send_api_request('wall.get',
                                     {'owner_id': group_id,
                                      'offset': 0,
                                      'count': 13,
                                      'filter': 'owner'})
        latest = next(iter(i for i in data['response']['items']
                           if i.get('is_pinned') != 1))
        now = time.time()
        if attempts is None:
            return latest['id'], datetime.datetime.fromtimestamp(latest['date'])
        if now - latest['date'] > 666:
            time.sleep(1)
            return self.get_latest_post_and_time(group_id, attempts - 1)
        return latest['id'], datetime.datetime.fromtimestamp(latest['date'],
                                                             tz=get_local_tz())

    def add_comment(self, group_id, post_id, comment_text):
        data = self.send_api_request('wall.createComment',
                                     {'post_id': post_id,
                                      'owner_id': group_id,
                                      'message': comment_text})
        return data['response']['comment_id']
