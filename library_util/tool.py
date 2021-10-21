import argparse
import datetime
import json
from os import path, makedirs
import random
import requests
from library_util.xtulib import classroom
import http.cookiejar
import urllib.request
import urllib.parse

# 配置文件名称项
LIBRARY = 'LIBRARY'
reserve = 'reserve'
user_login = 'user_login'
lib = 'lib'
seat = 'seat'
seat_random = 'random'
prems = 'prems'
user = 'user'
app_id = 'app_id'
user_id = 'user_id'
company_id = 'company_id'
company_secret = 'company_secret'
day = 'day'
# 通知配置
touser = "@all"
agentId = None
corpid = None
corpsecret = None
# 抓xd校园的包,提取链接类似http://wechat.v2.traceint.com/index.php/schoolpushh5/registerLogin?sch_id=
login_url = ""
# 要占座的座位列表
seat_dict = {}
# 提前多少秒开抢 支持三位小数
preMs = 0.1
# 是否抢位置
RUN = True
# 是否随机位置,每天不在一个位置
ran = False
# 用户名称
user_name = 'test'
day_list = []

# redis 配置
redis_host = '127.0.0.1'
redis_port = 6379
redis_db = 0
redis_key = 'access_token'
expire_key = 'expires_in'
redis_conn = None

# 默认的抢座列表
default_seat = {"南204中文图书借阅一厅(2楼)": [1, 2, 3, 4, 5, 6, 7, 8]}
# 抢座链接 根据lib_id YsjhY856两个参数确定座位
url_submit = 'http://wechat.v2.traceint.com/index.php/reserve/get/'
# 带有生成参数的js文件链接的页面链接
url_hex = "http://wechat.v2.traceint.com/index.php/reserve/layout/libid=%s.html"

# 构建一个CookieJar对象实例来保存cookie
cookiejar = http.cookiejar.CookieJar()
handler = urllib.request.HTTPCookieProcessor(cookiejar)
opener = urllib.request.build_opener(handler)


def write_log(temp_content):
    # 创建图片和日志路径
    log_path = '../log/'
    if not path.exists(log_path):
        makedirs(log_path)
    with open(log_path + 'library.log', 'a+', encoding='utf-8') as log_file:
        log_file.seek(0, 0)
        log_file.write(temp_content)


def get_token(REDIS_OPEN, temp_redis_conn, temp_corpid, temp_corpsecret):
    access_token = None
    if REDIS_OPEN:
        access_token = temp_redis_conn.get(redis_key)
    if not access_token:
        get_token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={temp_corpid}&corpsecret={temp_corpsecret}"
        response = requests.get(get_token_url).text
        response = json.loads(response)
        access_token = response.get(redis_key)
        expires_in = response.get(expire_key)
        # print(access_token)
        if REDIS_OPEN:
            temp_redis_conn.set(redis_key, access_token, nx=True, ex=expires_in)
    if type(access_token) is bytes:
        access_token = str(access_token, encoding="utf-8")
    return access_token


def check_conf(temp_conf):
    conf_list = [reserve, user_login, lib, seat, seat_random, prems, company_id, company_secret, app_id, user, user_id,day]
    conf_list.sort()
    temp_conf.sort()
    return conf_list == temp_conf


def get_args():
    parser = argparse.ArgumentParser(description='Test for argparse')
    parser.add_argument('--conf', '-c', help='用户文件配置文件路径,必要参数', required=True)
    args = parser.parse_args()
    temp_conf_path = args.conf
    return temp_conf_path


def get_temp_seat(input_seat_dict, input_ran):
    temp_seat_dict = {}
    lib_name_list = list(input_seat_dict.keys())
    if input_ran:
        random.shuffle(lib_name_list)
    for lib_name in lib_name_list:
        print(lib_name, " 座位号: ", end='')
        temp_lib = classroom[lib_name]
        temp_lib_id = str(list(temp_lib.keys())[0])
        seat_key_list = []
        seat_list = input_seat_dict[lib_name]
        if input_ran:
            random.shuffle(seat_list)
        for seat_num in seat_list:
            seat_num = str(seat_num)
            print(seat_num, " ", end='')
            temp_seat_key = classroom[lib_name][temp_lib_id][seat_num]
            seat_key_list.append(temp_seat_key)
        temp_seat_dict[temp_lib_id] = seat_key_list
        print()
    return temp_seat_dict


def init_seat_dict(input_seat_dict=None, input_ran=False):
    if not input_seat_dict:
        print('--------------未选择座位,将使用默认座位--------------')
        input_seat_dict = default_seat
    print('--------------本次选择座位列表--------------')
    temp_seat_dict = get_temp_seat(input_seat_dict, input_ran)
    return temp_seat_dict


def get_time():
    now_timeformat = '%Y-%m-%d %H:%M:%S'
    submit_time = datetime.datetime.now().strftime(now_timeformat)
    return submit_time
