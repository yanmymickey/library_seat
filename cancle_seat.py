import configparser
import redis
import time

from library_util.tool import *

# 状态
res_code = 1
moment = False
selected = False
REDIS_OPEN = True
isNotify = False


# 微信通知
def notify_wechat(text, desp, temp_REDIS_OPEN, temp_redis_conn, temp_corpid, temp_corpsecret):
    if not isNotify:
        return
    access_token = get_token(temp_REDIS_OPEN, temp_redis_conn, temp_corpid, temp_corpsecret)
    if access_token and len(access_token) > 0:
        send_msg_url = f'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}'
        data = {
            "touser": touser,
            "agentid": agentId,
            "msgtype": "textcard",
            "textcard": {
                "title": user_name + " " + text,
                "description": user_name + "\n" + desp,
                "url": login_url,
                "btntxt": "more"
            },
            "duplicate_check_interval": 600
        }
        requests.post(send_msg_url, data=json.dumps(data))


# 以get方法访问登录链接，访问之后会自动保存cookie到cookiejar中
def sleep_to_time():
    # 分
    h = int(datetime.datetime.now().strftime('%H'))
    # 分
    m = int(datetime.datetime.now().strftime('%M'))
    # 秒
    s = int(datetime.datetime.now().strftime('%S'))
    if m < 28 and h == 9:
        time.sleep(60 * 29 - 60 * m - s)


def get_time():
    now_timeformat = '%Y-%m-%d %H:%M:%S'
    submit_time = datetime.datetime.now().strftime(now_timeformat)
    return submit_time


def read_conf(temp_conf):
    global login_url, user_name, touser, agentId, corpid, corpsecret, isNotify
    user_name = temp_conf.get(LIBRARY, user)
    login_url = temp_conf.get(LIBRARY, user_login)
    touser = temp_conf.get(LIBRARY, user_id)
    agentId = temp_conf.get(LIBRARY, app_id)
    corpid = temp_conf.get(LIBRARY, company_id)
    corpsecret = temp_conf.get(LIBRARY, company_secret)
    if not corpid or not corpsecret or not app_id:
        isNotify = False
        print("--------------没有提供完整的企业微信配置信息,将不会产生微信通知--------------")


def get_cancel_token():
    cancel_token_url = "http://wechat.v2.traceint.com/index.php/reserve/token.html"
    cancel_body = {
        'type': 'cancle'
    }
    cancel_body = urllib.parse.urlencode(cancel_body).encode('utf-8')
    res_html = opener.open(cancel_token_url, data=cancel_body).read().decode('utf-8')
    res = json.loads(res_html)
    if res['code'] == 0:
        return res['msg']
    else:
        return None


def cancel_seat(temp_token):
    cancel_seat_url = "http://wechat.v2.traceint.com/index.php/cancle/index?t=%s" % temp_token
    res_html = opener.open(cancel_seat_url).read().decode('utf-8')
    return res_html


# 以get方法访问登录链接，访问之后会自动保存cookie到cookiejar中
def login():
    if login_url != "":
        return opener.open(login_url).read().decode('utf-8')


print("--------------begin cancel seat--------------")
if REDIS_OPEN:
    try:
        redis_conn = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
        redis_conn.ping()
    except Exception as e:
        REDIS_OPEN = False
        print(e)
        print("--------------未开启redis,不使用redis--------------")
conf = configparser.RawConfigParser()
conf_path = get_args()
conf.read(conf_path, encoding='utf-8-sig')
if LIBRARY not in conf.sections():
    print('--------------配置文件格式错误--------------')
    exit()
conf_options_list = list(conf.options(LIBRARY))
if not check_conf(conf_options_list):
    print('--------------配置文件格式错误--------------')
    exit()
# 读取配置文件
try:
    read_conf(conf)
except Exception as e:
    print('--------------读取配置' + conf_path + '文件失败,配置文件格式错误--------------')
    error_text = "脚本运行错误报告"
    error_desp = get_time() + "读取配置" + conf_path + "文件失败,配置文件格式错误"
    write_log(error_desp)
    notify_wechat(error_text, error_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)
    exit(3)
start_text = "脚本开始运行"
start_desp = get_time() + "退坐脚本开始运行"
notify_wechat(start_text, start_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)

if login_url != "":
    index_html = login()
    token = get_cancel_token()
    if token is not None:
        cancel_seat_html = cancel_seat(token)
        if "本次学习时长" in cancel_seat_html:
            cancel_text = "退座成功通知"
            cancel_desp = get_time() + "退座成功"
            write_log(cancel_desp)
            notify_wechat(cancel_text, cancel_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)
        elif "您还没有预定座位" in cancel_seat_html:
            error_text = "脚本运行错误报告"
            error_desp = get_time() + "没有预定座位,退坐失败"
            write_log(error_desp)
            notify_wechat(error_text, error_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)
        else:
            error_text = "脚本运行错误报告"
            error_desp = get_time() + "退坐失败"
            write_log(error_desp)
            notify_wechat(error_text, error_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)
    else:
        error_text = "脚本运行错误报告"
        error_desp = get_time() + "token==None退坐失败"
        write_log(error_desp)
        notify_wechat(error_text, error_desp, REDIS_OPEN, redis_conn, corpid, corpsecret)