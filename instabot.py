from pprint import pprint

import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InputMediaPhoto, InputMediaVideo
from config import *
from time import sleep
import requests
import json


def get_data(post_url):
    source = requests.get(post_url).text
    first_index = source.find('<script type="text/javascript">window._sharedData = ') + 52
    last_index = source.find(';</script>', first_index)
    return json.loads(source[first_index:last_index])


def media_url_generator(the_data):
    for media in the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']:
        if media['node']['is_video']:
            yield media['node']['video_url']

        else:
            yield media['node']['display_url']


def get_caption(the_data):
    return the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_media_to_caption']['edges'][0]['node']['text']


def message_handler(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    if chat_type == u'private':
        if content_type == 'text':
            if msg['text'] == '/start':
                bot.sendMessage(chat_id, start_msg)

            else:
                the_data = get_data(msg['text'])
                '''file = open('sigvid.py', 'w')
                pprint(the_data, stream=file)
                file.close()
                print('*********')#'''

                try:
                    post_caption = get_caption(the_data)
                    if len(post_caption) > 1024:
                        bot.sendMessage(chat_id, post_caption)
                        post_caption = ''

                except IndexError:
                    post_caption = ''

                except KeyError:
                    if the_data['entry_data']['ProfilePage'][0]['graphql']['user']['is_private']:
                        bot.sendMessage(chat_id, private_msg)

                    else:
                        bot.sendMessage(chat_id, error_msg)
                    return

                try:
                    album = []
                    for media_url in media_url_generator(the_data):
                        if media_url.find('.jpg') != -1:
                            input_media = InputMediaPhoto(type='photo', media=media_url, caption=post_caption)

                        else:
                            input_media = InputMediaVideo(type='video', media=media_url, caption=post_caption)

                        album.append(input_media)

                    bot.sendMediaGroup(chat_id, album)

                except KeyError:
                    try:
                        video_url = the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['video_url']
                        bot.sendVideo(chat_id, video_url, caption=post_caption)

                    except KeyError:
                        pic_url = the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['display_resources'][-1]['src']
                        bot.sendPhoto(chat_id, pic_url, caption=post_caption)




bot =  telepot.Bot(TOKEN)

MessageLoop(bot, message_handler).run_as_thread()

print('Program is running...')

while True:
    sleep(30)
