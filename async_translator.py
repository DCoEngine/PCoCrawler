import asyncio

import aiohttp
import requests


class TranslateTask:
    """翻译任务数据类
    
    封装翻译任务的相关参数和结果，用于Google翻译API请求。

    Attributes:
        langfrom (str): 源语言代码，默认为'en'
        langto (str): 目标语言代码，默认为'zh-CN'
        raw (str): 待翻译的原始文本
        result (str): 翻译结果文本
        secret (str): 自定义翻译API端点URL
    """
    def __init__(self, raw, langfrom="en", langto="zh-CN", result=None, secret=None):
        self.langfrom = langfrom
        self.langto = langto
        self.raw = raw
        self.result = result
        self.secret = secret


def TL(a):
    """
    参考zotero翻译插件的代码
    https://github.com/windingwind/zotero-pdf-translate/blob/main/src/modules/services/google.ts
    """

    def RL(a, b):
        """Google翻译的token生成算法辅助函数
        
        实现Google翻译API的token生成算法中的位运算部分。

        Args:
            a (int): 初始数值
            b (str): 操作符字符串

        Returns:
            int: 经过位运算处理后的结果
        """
        t = "a"
        Yb = "+"
        for c in range(0, len(b) - 2, 3):
            d = b[c + 2]
            d = ord(d) - 87 if d >= t else int(d)
            d = (a >> d) if b[c + 1] == Yb else (a << d)
            a = (a + d & 4294967295) if b[c] == Yb else a ^ d
        return a

    b = 406644
    b1 = 3293161072

    jd = "."
    db = "+-a^+6"
    Zb = "+-3^+b+-f"

    e = []
    f = 0
    for g in range(len(a)):
        m = ord(a[g])
        if m < 128:
            e.append(m)
        else:
            if m < 2048:
                e.append(m >> 6 | 192)
            else:
                if 55296 == (m & 64512) and g + 1 < len(a) and 56320 == (ord(a[g + 1]) & 64512):
                    m = 65536 + ((m & 1023) << 10) + (ord(a[g + 1]) & 1023)
                    g += 1
                    e.append(m >> 18 | 240)
                    e.append(m >> 12 & 63 | 128)
                else:
                    e.append(m >> 12 | 224)
                e.append(m >> 6 & 63 | 128)
            e.append(m & 63 | 128)

    a = b
    for f in e:
        a += f
        a = RL(a, db)
    a = RL(a, Zb)
    a ^= b1 or 0
    if a < 0:
        a = (a & 2147483647) + 2147483648
    a %= 1e6
    return str(a) + jd + str(int(a) ^ int(b))


async def async_google_translate(data, url="https://translate.googleapis.com", proxy=None):
    """
    参考zotero翻译插件的代码
    https://github.com/windingwind/zotero-pdf-translate/blob/main/src/modules/services/google.ts
    """
    error = 0
    while error <= 3:
        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                async with session.get(
                    f"{data.secret if data.secret else url}/translate_a/single",
                    proxy=proxy,
                    params={
                        "client": "gtx",
                        "hl": "zh-CN",
                        "dt": [
                            "at",
                            "bd",
                            "ex",
                            "ld",
                            "md",
                            "qca",
                            "rw",
                            "rm",
                            "ss",
                            "t",
                        ],
                        "source": "bh",
                        "ssel": "0",
                        "tsel": "0",
                        "kc": "1",
                        "tk": TL(data.raw),
                        "q": data.raw,
                        "sl": data.langfrom,
                        "tl": data.langto,
                    },
                ) as response:
                    response.raise_for_status()

                    result = ""
                    json_response = await response.json()
                    for item in json_response[0]:
                        if item and item[0]:
                            result += item[0]

                    data.result = result
                return
        except Exception as e:
            error += 1
            pass


async def async_translate(text, langto="zh-CN", proxy=None):
    task = TranslateTask(raw=text, langto=langto)
    await async_google_translate(task, proxy=proxy)
    return task.result


def google_translate(data, url="https://translate.googleapis.com", proxy=None):
    """同步调用Google翻译API
    
    使用requests库同步调用Google翻译API进行文本翻译。

    Args:
        data (TranslateTask): 翻译任务数据对象
        url (str): Google翻译API端点，默认为官方API
        proxy (str): 代理服务器地址，格式为"http://host:port"

    Raises:
        requests.exceptions.RequestException: 当API请求失败时抛出
    """
    response = requests.get(
        f"{data.secret if data.secret else url}/translate_a/single",
        params={
            "client": "gtx",
            "hl": "zh-CN",
            "dt": ["at", "bd", "ex", "ld", "md", "qca", "rw", "rm", "ss", "t"],
            "source": "bh",
            "ssel": "0",
            "tsel": "0",
            "kc": "1",
            "tk": TL(data.raw),
            "q": data.raw,
            "sl": data.langfrom,
            "tl": data.langto,
        },
        proxies={"https": proxy},
    )

    response.raise_for_status()  # 交由requests抛出异常

    result = ""
    for item in response.json()[0]:
        if item and item[0]:
            result += item[0]

    data.result = result


def translate(text, langto="zh-CN", proxy=None):
    task = TranslateTask(raw=text, langto=langto)
    google_translate(task, proxy=proxy)
    return task.result


# 示例Demo
async def main(proxy="http://127.0.0.1:7890"):
    """翻译功能示例演示
    
    展示如何使用异步和同步方式调用翻译功能。

    Args:
        proxy (str): 代理服务器地址，格式为"http://host:port"
    """
    text = await async_translate("Hello, world!", proxy=proxy)
    print(f"Async Translated text: {text}")
    print("Translated text:", translate("hello world", proxy=proxy))


if __name__ == "__main__":
    asyncio.run(main())
