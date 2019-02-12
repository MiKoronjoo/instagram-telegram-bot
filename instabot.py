import InstagramAPI
import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import InputMediaPhoto, InputMediaVideo, ReplyKeyboardMarkup, KeyboardButton, \
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
import time
import requests
import json
from config import *
from consts import *
import enum
import pickle
import os
import subprocess
import _thread
import random


def get_winners(followers, winners_num):
    winners = []
    i = 0
    while len(winners) != winners_num:
        i += 1
        winner = random.choice(followers)['username']
        if winner not in winners:
            winners.append('%d. %s' % (i, winner))

    return winners


def getTotalFollowers(api, username, msg_id):
    """
    Returns the list of followers of the user.
    It should be equivalent of calling api.getTotalFollowers from InstagramAPI
    """
    ###
    source = requests.get('https://instagram.com/' + username).text
    owner_str = '"owner":{"id":"'
    first_index = source.find(owner_str) + len(owner_str)
    last_index = source.find('"', first_index)
    user_id = int(source[first_index:last_index])

    count_str = '"userInteractionCount":"'
    first_index = source.find(count_str) + len(count_str)
    last_index = source.find('"', first_index)
    total = int(source[first_index:last_index])
    if total > 100000:
        raise Exception
    max_total = total
    if max_total > 20000:
        max_total = 20000
    ###
    followers = []
    next_max_id = True
    total_now = 0
    while next_max_id or total_now < max_total:
        # first iteration hack
        if next_max_id is True:
            next_max_id = ''
        _ = api.getUserFollowers(user_id, maxid=next_max_id)
        ###
        temp = api.LastJson.get('users', [])
        total_now += len(temp)
        progress_bar(msg_id, total_now, max_total)
        ###
        followers.extend(temp)
        next_max_id = api.LastJson.get('next_max_id', '')
    return followers, total


def progress_bar(msg_id: tuple, current_value: int, end_value: int) -> None:
    new_msg = int((current_value / end_value) * 100)
    if new_msg >= 100:
        new_msg = 99
    # if current_value:
    try:
        bot.editMessageText(msg_id, 'در حال قرعه‌کشی بین فالورها: {0}%'.format(new_msg))
    except telepot.exception.TelegramError:
        pass


def lottery(chat_id, username, winners_num):
    msg_id = chat_id, bot.sendMessage(chat_id, 'لطفا صبر کنید...')['message_id']
    try:
        followers, total = getTotalFollowers(api, username, msg_id)
    except Exception:
        bot.sendMessage(chat_id, fol_error)
        return
    winners = get_winners(followers, winners_num)
    wow = (lottery_msg % (username, total, winners_num, 'instagram.com/' + username)) + '\n'.join(winners)
    bot.deleteMessage(msg_id)
    bot.sendMessage(chat_id, wow)


def download_live(target_user, username=def_username, password=def_password):
    status, download_live_output = subprocess.getstatusoutput(
        'livestream_dl -u "%s" -p "%s" "%s" ' % (username, password, target_user))
    if status:
        raise Exception('failed')

    return download_live_output


def get_file_names(st):
    right_bound = 0
    while True:
        left_pivot = st.find('Generated file(s):', right_bound) + 1
        if not left_pivot:
            break
        left_bound = st.find('\n', left_pivot) + 1
        right_bound = st.find('\n', left_bound)
        yield st[left_bound:right_bound]


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

    return 'تعداد کل کاربران: %d\n\nتعداد کاربرانی که در ۲۴ساعت گذشته اضافه شده‌اند: %d' \
           % (len(users), len([x for x in times if x > this_time]))


state_msgs = {STATE.START: 'لطفا یک نام‌کاربری یا لینک یک پست اینستاگرام را بفرستید:',
              STATE.MANAGE: 'لطفا یکی از موارد را انتخاب کنید:',
              STATE.SEND_TO_ALL: 'لطفا یک پیغام برای ارسال به تمام کاربران وارد کنید:',
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


def story_url_generator(username):
    source = requests.get('https://storiesig.com/stories/' + username).text
    last_index = 0
    download_str = 'download"><a href="'
    while True:
        first_index = source.find(download_str, last_index) + len(download_str)
        if first_index == len(download_str) - 1:  # Not found
            break
        last_index = source.find('"', first_index)
        yield source[first_index:last_index]


def get_live(username):
    print(username)
    os.system('livestream_dl -u "myfirstpj" -p "w951q951" "%s"' % username.replace('/', ''))


def get_caption(the_data):
    return the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['edge_media_to_caption']['edges'][0][
        'node']['text']


# def get_profile_pic(the_data):
#     return the_data['entry_data']['ProfilePage'][0]['graphql']['user']['profile_pic_url_hd']


def keyboard_maker(keyboard_labels):
    my_keyboard = []
    for row in keyboard_labels:
        keyboard_row = []
        for label in row:
            keyboard_row.append(KeyboardButton(text=label))

        my_keyboard.append(keyboard_row)

    return ReplyKeyboardMarkup(keyboard=my_keyboard, resize_keyboard=True)


def inline_keyboard_maker(keyboard_labels):
    my_keyboard = []
    for row in keyboard_labels:
        keyboard_row = []
        for label in row:
            text, callback_data = label
            keyboard_row.append(InlineKeyboardButton(text=text, callback_data=callback_data))

        my_keyboard.append(keyboard_row)

    return InlineKeyboardMarkup(inline_keyboard=my_keyboard)


def get_keyboard(user_id):
    if user_id == admin_id:
        if users[user_id] == STATE.START:
            return keyboard_maker([['مدیریت']])

        elif users[user_id] == STATE.MANAGE:
            return keyboard_maker([['پیغام به اعضا'], ['آمار بات'], ['بازگشت']])

        elif users[user_id] in [STATE.SEND_TO_ALL, STATE.BOT_STATISTICS]:
            return keyboard_maker([['بازگشت']])

    return ReplyKeyboardRemove(remove_keyboard=True)


def helper_send_file(msg):
    try:
        file_id = msg['video']['file_id']
        user_id = msg['caption']
        bot.sendMessage(user_id, this_live)
        bot.sendVideo(user_id, file_id)
    except Exception as ex:
        print(ex)


def handle_pv(msg):
    global users
    content_type, _, user_id = telepot.glance(msg)
    if user_id == helper_id and content_type == 'video':
        helper_send_file(msg)
        return

    if content_type == 'text':
        if msg['text'] == '/start':
            bot.sendMessage(user_id, start_msg, reply_markup=get_keyboard(user_id))

        elif msg['text'] == 'بازگشت':
            if users[user_id] == STATE.MANAGE:
                users.update({user_id: STATE.START})

            elif users[user_id] == STATE.SEND_TO_ALL:
                users.update({user_id: STATE.MANAGE})

            elif users[user_id] == STATE.BOT_STATISTICS:
                users.update({user_id: STATE.MANAGE})


        elif msg['text'] == 'مدیریت' and users[user_id] == STATE.START and user_id == admin_id:
            users.update({user_id: STATE.MANAGE})

        elif msg['text'] == 'پیغام به اعضا' and users[user_id] == STATE.MANAGE:
            users.update({user_id: STATE.SEND_TO_ALL})

        elif msg['text'] == 'آمار بات' and users[user_id] == STATE.MANAGE:
            bot.sendMessage(user_id, statistics())

        elif users[user_id] == STATE.BOT_STATISTICS:
            users.update({user_id: STATE.MANAGE})

        elif users[user_id] == STATE.SEND_TO_ALL:
            send_to_all(msg['text'])
            bot.sendMessage(user_id, 'با موفقیت ارسال شد')
            users.update({user_id: STATE.MANAGE})

        else:
            ##### lottery #####
            if 'reply_to_message' in msg and msg['text'].isdigit():
                if int(msg['text']) > 200:
                    bot.sendMessage(user_id, num_error)
                    return
                try:
                    username = msg['reply_to_message']['text'].split('@')[-1]
                    winners_num = int(msg['text'])
                    lottery(user_id, username, winners_num)
                except:
                    bot.sendMessage(user_id, bad_input)
                return
            ###################
            try:
                username = msg['text'].split('instagram.com/')[-1].split('?')[0].replace('/', '').lower()
                source = requests.get('https://www.instagram.com/' + username).text
                if source.find('profile_pic_url_hd":"') != -1:
                    #
                    fn_str = '"full_name":"'
                    first_index = source.find(fn_str) + len(fn_str)
                    last_index = source.find('"', first_index)
                    full_name = source[first_index:last_index]
                    #
                    try:
                        full_name = eval(('"' + full_name + '"').replace('\\\\u', '\\\\u'))
                        print(full_name)
                    except UnicodeEncodeError:
                        full_name = source[first_index:last_index]
                    #
                    bot.sendMessage(user_id, user_info % (full_name, username, 'instagram.com/' + username), 'Markdown',
                                    reply_markup=inline_keyboard_maker(
                                        [[('دانلود عکس پروفایل', username + ' profile')],
                                         [('دانلود استوری‌ها', username + ' story')],
                                         [('دانلود لایوها', username + ' live')],
                                         [('قرعه‌کشی بین اعضای پیج', username + ' lottery')]
                                         ]
                                    )
                                    )
                    return
                else:
                    wait_msg_id = bot.sendMessage(user_id, wait_msg)['message_id']
                    ########## Load data ##########
                    try:
                        the_data = get_data(msg['text'])

                    except:
                        bot.deleteMessage((user_id, wait_msg_id))
                        bot.sendMessage(user_id, bad_input, reply_markup=get_keyboard(user_id))
                        return

                    ########## Send caption ##########
                    try:
                        post_caption = get_caption(the_data)
                        has_caption = True

                    except IndexError:
                        has_caption = False

                    except KeyError:
                        bot.deleteMessage((user_id, wait_msg_id))
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
                                input_media = InputMediaPhoto(type='photo', media=media_url)

                            else:
                                input_media = InputMediaVideo(type='video', media=media_url)

                            album.append(input_media)

                        bot.deleteMessage((user_id, wait_msg_id))
                        bot.sendMessage(user_id, this_posts)
                        bot.sendMediaGroup(user_id, album)

                    ########## Single media ##########
                    except KeyError:
                        ########## Send video ##########
                        try:
                            video_url = the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']['video_url']
                            bot.deleteMessage((user_id, wait_msg_id))
                            bot.sendMessage(user_id, this_post)
                            bot.sendVideo(user_id, video_url)

                        ########## Send Photo ##########
                        except KeyError:
                            pic_url = the_data['entry_data']['PostPage'][0]['graphql']['shortcode_media'][
                                'display_resources'][-1]['src']
                            bot.deleteMessage((user_id, wait_msg_id))
                            bot.sendMessage(user_id, this_post)
                            bot.sendPhoto(user_id, pic_url)

                    if has_caption:
                        bot.sendMessage(user_id, this_caption)
                        bot.sendMessage(user_id, post_caption)


            except Exception as ex:
                print(ex)
                bot.sendMessage(user_id, bad_input)


def message_handler(msg):
    _thread.start_new_thread(my_message_handler, (msg,))
    return


def my_message_handler(msg):
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


def callback_query(msg):
    _thread.start_new_thread(my_callback_query, (msg,))
    return


def my_callback_query(msg):
    query_id, from_id, query_data = telepot.glance(msg, flavor='callback_query')
    print(query_id, from_id, query_data)
    username, which = query_data.split()
    en2fa = {'profile': 'عکس پروفایل', 'story': 'استوری', 'live': 'لایو'}
    try:
        bot.answerCallbackQuery(query_id, 'در حال دانلود %s... لطفا شکیبا باشید' % en2fa[which])
    except KeyError:
        pass

    if which == 'profile':
        url = 'https://www.instagram.com/' + username
        source = requests.get(url).text
        prof_str = 'profile_pic_url_hd":"'
        first_index = source.find(prof_str) + len(prof_str)
        last_index = source.find('"', first_index)
        bot.sendMessage(from_id, this_pro_pic)
        bot.sendPhoto(from_id, source[first_index:last_index])

    elif which == 'story':
        album = []
        for story_url in story_url_generator(username):
            if story_url.find('.jpg') != -1:
                input_media = InputMediaPhoto(type='photo', media=story_url)

            else:
                input_media = InputMediaVideo(type='video', media=story_url)

            album.append(input_media)

        if album:
            bot.sendMessage(from_id, this_story)
            while album:
                bot.sendMediaGroup(from_id, album[:10])
                album = album[10:]

        else:
            bot.sendMessage(from_id, story_not_found)

    elif which == 'live':
        srch_msg_id = bot.sendMessage(from_id, 'درحال جستجو لایو...')['message_id']
        gen = get_file_names(download_live(username))
        found = False
        for file_name in gen:
            found = True
            bot.editMessageText((from_id, srch_msg_id), 'درحال آپلود لایو روی سرور تلگرام...')
            os.system('python3 upload_file.py %s %s' % (file_name, from_id))

        os.system('rm -rf downloaded')
        if not found:
            bot.sendMessage(from_id, live_not_found)

        bot.deleteMessage((from_id, srch_msg_id))

    elif which == 'lottery':
        bot.sendMessage(from_id, lottery_info)


api = InstagramAPI.InstagramAPI(def_username, def_password)
api.login()
print('Instagram logged in')

bot = telepot.Bot(TOKEN)

MessageLoop(bot, {'chat': message_handler, 'callback_query': callback_query}).run_as_thread()

print('Program is running...')

while True:
    time.sleep(30)
