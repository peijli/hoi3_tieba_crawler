# 作者：百度贴吧 @pl_mich
# 致谢：
# https://blog.csdn.net/zhaobig/article/details/77198978 及其作者 @纳尔逊皮卡丘
# https://www.jianshu.com/p/27c534394890 及其作者 @小新你蜡笔呢
# https://stackoverflow.com/a/23761093 及其作者 @NorthCat
# 前排提醒：在python之前我先学的是java语言，所以这里的有些docstring我是用近似javadoc格式
# 的Epytext写的；另外本人写python时有单双引号混用的缺点，敬请谅解……

# 本程序会使用到两个第三方模块: pdfkit与wkhtmltopdf。其中pdfkit可以通过python命令窗口中
# pip install pdfkit取得；而wkhtmltopdf可以通过https://wkhtmltopdf.org/downloads.html
# 下载安装程序，windows系统用户就安装到默认的C:\Program Files\wkhtmltopdf\下

import urllib
import re
import pdfkit
import requests
import socket
from os import path

# 为了使pdfkit以及其后台的wkhtmltopdf正常工作，需要以此config变量指明wkhtmltopdf的
# 可执行文件的路径
config = pdfkit.configuration(
    wkhtmltopdf = 'C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')


def process(str) -> str:
    '''将Windows系统识别为非法的字符删去'''
    if len(str) > 240: str = str[0,240]
    return ''.join(re.split('[\\/:"*?<>|]+', str.strip()))


def convert_post(id_title_tuple: tuple) -> bool:

    '''将某一篇贴子转换为pdf文件保存

    @param id_title_tuple 一个包括某贴访问id和标题的元组，形如
        ("/p/938221848?fr=good","1.4版36年VH难度民国攻略教程（附带36中国MOD）")

    @return 表示贴子转换是否成功的布尔函数；本来是想用try/except来做一个自动重复爬取保存
        失败的贴子的功能，但好像几乎每个贴子转换时都会有大大小小的问题出现，
        所以几乎一直返回False……唉，所谓“爬虫”只是条“虫”也是有道理的(汗)
    '''

    # 用正则匹配处理贴子的访问id，最终的ide变量中储存的应该是形如'938221848'的纯数字构成的
    # 字符串；另外还有机制专门制止形如('/bawu2/errorPage?bz=1', '本吧吧主火热招募中，点击参加')
    # 的bug元组
    if 'bawu' in id_title_tuple[0]: return True
    patt = re.compile(r'(.+)\?fr=good')
    prelim_ide = id_title_tuple[0][3:]
    if patt.match(prelim_ide) == None: ide = prelim_ide
    else: ide = patt.findall(prelim_ide)[0]

    # 删去贴子标题中可能出现的Windows系统认定无法作为文件名一部分的特殊字符
    title = process(id_title_tuple[1])

    # 拼接完整URL和文件名
    url = 'https://tieba.baidu.com/p/' + ide
    filename = "[%s]%s.pdf" % (ide, title)

    # 发起请求获取第一页源代码，利用正则匹配在其中找到总页数，并储存到total变量中
    response = urllib.request.urlopen(url)
    pattern = re.compile(
        '<li class="l_reply_num.*?<span.*?<span class="red">(.*?)</span>',re.S)
    html = response.read().decode()
    rs = re.search(pattern, html)
    total = int(rs.group(1))

    # 如果目标pdf已存在，则跳过后续爬虫过程
    if path.exists(filename):
        print("目标文件%s已存在！" % filename)
        return True

    print('正在爬取%s,共%s页数据' % (title,total))

    # 创建用来存储所有页码URL的数组
    url_list = []
    # 循环获取每一页贴子的URL，形如https://tieba.baidu.com/p/6854845304?pn=2
    for x in range(1, total + 1):
        getUrl = url + '?pn=%s' % x
        print(getUrl)
        url_list.append(getUrl)
    
    # 导出pdf文件
    try:
        print("正在保存为pdf，请稍候……")

        # pdfkit的另外一个设置——如果不让它“忽略”所有爬取中出现的各种大小错误，
        # 则不仅程序运行会中断，而且不会有任何pdf文件生成
        options = {'load-error-handling': 'ignore'}
        pdfkit.from_url(
            url_list, filename, configuration = config, options = options)
        print("pdf保存完成！")
        return True

    except:
        # 好吧，正如我之前所说的，在90%的情况下pdfkit都会反馈各种大小错误，所以几乎每一次
        # 都得执行这个except程序块
        return False


def get_html(url: str) -> str:

    ''' 
    从精品贴目录中的某一页中，使用对于html源代码的正则匹配，提取所有贴子链接

    @return 包括所有访问id和贴子标题的元组构成的数组，其中每一项形如
        ("/p/938221848?fr=good","1.4版36年VH难度民国攻略教程（附带36中国MOD）")
    '''

    response = urllib.request.urlopen(url)
    html = response.read().decode()
    patt = re.compile(
        '<div.*?j_threadlist_li_right.*?>.*?<a.*?href=\"(.*?)\".*?>(.*?)</a>', re.S)
    return re.findall(patt, html)
  

def get_post_id_list() -> list:

    '''
    从钢3吧中提取所有精品贴的访问id和贴子标题的元组；钢3吧一共就只有12页精品贴，
    我也希望这个程序只会用到极少数的贴吧上，所以就舍去了从精品贴目录第一页的源代码中
    提取精品贴页数的想法——毕竟正则匹配的语句太太太太难写了(泪)

    @return 以上元组构成的数组
    '''

    i = 0
    return_list = []

    # 百度贴吧精品贴的目录并不是按照正整数来编号的，而是按照以0为首项、50为公差的等差数列
    # 标号的，比如钢3吧精品贴目录第一页为
    # https://tieba.baidu.com/f/good?kw=钢铁雄心3&tab=good&cid=&pn=0
    # 第二页为https://tieba.baidu.com/f/good?kw=钢铁雄心3&tab=good&cid=&pn=50
    # 理论上是应该一页有50篇贴子，12页总共556个精品贴的；但是钢3吧在经过历年来百度的
    # 清洗过后精品贴实际只有421个可以访问

    while i <= 550:
        url = 'https://tieba.baidu.com/f?kw=%E9%92%A2%E9%93%81%E9%9B%84%E5%BF%833&ie=utf-8&tab=good&cid=&pn=' + str(i)
        return_list.extend(get_html(url))
        i += 50
        print("%d页精品贴链接提取完成" % (i / 50))
        print(len(return_list))
    return return_list  
    

if __name__ == "__main__":

    # 提取所有精品贴的访问id和贴子标题的元组
    id_list = get_post_id_list()

    # 将每一个精品贴对应的元组打印出来——测试用
    # for id_title_tuple in id_list:
    #     print(id_title_tuple)
    
    # 将每一个精品贴保存为pdf
    for id_title_tuple in id_list:
        convert_post(id_title_tuple)
