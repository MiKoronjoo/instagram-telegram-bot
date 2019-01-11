import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InputMediaPhoto, InputMediaVideo, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove
import time
import requests
import json
from config import *
import enum
import pickle


class STATE(enum.Enum):
    START = 'START'
    MANAGE = 'MANAGE'
    SEND_TO_ALL = 'SEND_TO_ALL'
    BOT_STATISTICS = 'BOT_STATISTICS'


########## Load bot data ##########
try:
    file = open('instabot.db', 'rb')
    users, times = pickle.load(file)
    file.close()

except FileNotFoundError:
    users = {}
    times = []
###################################

def send_to_all(admin_msg):
    for user_id in users:
        try:
            bot.sendMessage(user_id, admin_msg)

        except telepot.exception.TelegramError:
            pass


def statistics():
    day = 24 * 60 * 60
    this_time = time.time() - day

    return 'Total users: %d\n\nUsers in last 24 hours: %d' % (len(users), len([x for x in times if x > this_time]))


state_msgs = {STATE.START: 'Send an instagram post link',
              STATE.MANAGE: 'Choose one of the options:',
              STATE.SEND_TO_ALL: 'Enter a message to send to all users:',
              STATE.BOT_STATISTICS: statistics()
              }


def get_data(post_url):
    source = requests.get(post_url).text
    script_str = '<script type="text/javascript">window._sharedData = '
    first_index = source.find(script_str) + len(script_str)
    last_index = source.find(';</script>', first_index)
    all_data = source[first_index:last_index]
    return json.loads(all_data)


def media_url_generator(the_data):
    for media in the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_sidecar_to_children'][
        'edges']:
        if media['node']['is_video']:
            yield media['node']['video_url']

        else:
            yield media['node']['display_url']


def get_caption(the_data):
    return the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_media_to_caption']['edges'][0][
        'node']['text']


def keyboard_maker(keyboard_labels):
    my_keyboard = []
    for row in keyboard_labels:
        keyboard_row = []
        for label in row:
            keyboard_row.append(KeyboardButton(text=label))

        my_keyboard.append(keyboard_row)

    return ReplyKeyboardMarkup(keyboard=my_keyboard)


def get_keyboard(user_id):
    if user_id == admin_id:
        if users[user_id] == STATE.START:
            return keyboard_maker([['Manage']])

        elif users[user_id] == STATE.MANAGE:
            return keyboard_maker([['Send message to users'], ['Bot statistics'], ['Back']])

        elif users[user_id] in [STATE.SEND_TO_ALL, STATE.BOT_STATISTICS]:
            return keyboard_maker([['Back']])

    return ReplyKeyboardRemove(remove_keyboard=True)


'''
def get_users():
    output = 'New users:\n'
    el = []
    for user_id in users:
        el.append(user_id)

    for user_id in el[-1:-10:-1]:
        output += '[%s](tg://user?id=%d)\n' % (users[user_id], user_id)

    output += '\nNumber of all users: %d' % len(users)

    return output#'''


def handle_pv(msg):
    global users
    content_type, _, user_id = telepot.glance(msg)
    if content_type == 'text':
        if msg['text'] == '/start':
            bot.sendMessage(user_id, start_msg, reply_markup=get_keyboard(user_id))

        elif msg['text'] == 'Back':
            if users[user_id] == STATE.MANAGE:
                users.update({user_id: STATE.START})

            elif users[user_id] == STATE.SEND_TO_ALL:
                users.update({user_id: STATE.MANAGE})

            elif users[user_id] == STATE.BOT_STATISTICS:
                users.update({user_id: STATE.MANAGE})


        elif msg['text'] == 'Manage' and users[user_id] == STATE.START and user_id == admin_id:
            users.update({user_id: STATE.MANAGE})

        elif msg['text'] == 'Send message to users' and users[user_id] == STATE.MANAGE:
            users.update({user_id: STATE.SEND_TO_ALL})

        elif msg['text'] == 'Bot statistics' and users[user_id] == STATE.MANAGE:
            bot.sendMessage(user_id, statistics())

        elif users[user_id] == STATE.BOT_STATISTICS:
            users.update({user_id: STATE.MANAGE})

        elif users[user_id] == STATE.SEND_TO_ALL:
            send_to_all(msg['text'])
            bot.sendMessage(user_id, 'Sent successfully!')
            users.update({user_id: STATE.MANAGE})

        else:
            ########## Load data ##########
            try:
                the_data = get_data(msg['text'])

            except:
                bot.sendMessage(user_id, bad_input, reply_markup=get_keyboard(user_id))
                return

            ########## Send caption ##########
            try:
                post_caption = get_caption(the_data)
                if len(post_caption) > 1024:
                    bot.sendMessage(user_id, post_caption)
                    post_caption = ''

            except IndexError:
                post_caption = ''

            except KeyError:
                if the_data['entry_data']['ProfilePage'][0]['graphql']['user']['is_private']:
                    bot.sendMessage(user_id, private_msg)

                else:
                    bot.sendMessage(user_id, error_msg)
                return

            ########## Send media group ##########
            try:
                album = []
                for media_url in media_url_generator(the_data):
                    if media_url.find('.jpg') != -1:
                        input_media = InputMediaPhoto(type='photo', media=media_url, caption=post_caption)

                    else:
                        input_media = InputMediaVideo(type='video', media=media_url, caption=post_caption)

                    album.append(input_media)

                bot.sendMediaGroup(user_id, album)

            ########## Single media ##########
            except KeyError:
                ########## Send video ##########
                try:
                    video_url = the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['video_url']
                    bot.sendVideo(user_id, video_url, caption=post_caption)

                ########## Send Photo ##########
                except KeyError:
                    pic_url = \
                        the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['display_resources'][-1][
                            'src']
                    bot.sendPhoto(user_id, pic_url, caption=post_caption)


def message_handler(msg):
    global users
    content_type, chat_type, chat_id = telepot.glance(msg)
    if chat_type == u'private':
        if chat_id not in users:
            users.update({chat_id: STATE.START})
            times.append(time.time())
            ########## Save bot data ##########
            file = open('instabot.db', 'wb')
            pickle.dump((users, times), file)
            file.close()

        handle_pv(msg)
        bot.sendMessage(chat_id, state_msgs[users[chat_id]], reply_markup=get_keyboard(chat_id))



bot = telepot.Bot(TOKEN)

MessageLoop(bot, message_handler).run_as_thread()

print('Program is running...')

while True:
    time.sleep(30)
