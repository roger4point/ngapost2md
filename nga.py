#nga.py by ludoux
# -*- coding: UTF-8 -*-
import re
import requests
import os
import sys
import time
from contextlib import closing
import hashlib
import json

#=============先修改
headers = {
    'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'}
cookies = {
    'ngaPassportUid': '60580951',
    'ngaPassportCid': 'X8q2su1c9lqaoplsncfjm5mkuebtbavodr5969i0',
}
#=============先修改
totalfloor = []  # int几层，int pid, str时间，str昵称，str内容，int赞数
tid = 0
title = 'title'
localmaxpage = 1
localmaxfloor = -1
# (在single里用)部分楼层有评论，content是挂在被评论楼层的，所以先放在这里，之后判断当前楼层是否是评论楼层（是的话没有content），是的话就直接读成这里 int pid，str时间，str昵称，str内容，int赞数
commentreply = []
errortext = ''

def single(page):
    print('trypage%d' % page)
    params = (
        ('tid', tid),
        ('page', page),
        ('lite', 'js')
    )
    ss1 = requests.Session()
    get = ss1.get('https://bbs.nga.cn/read.php', headers=headers,
                  params=params, cookies=cookies)
    get.encoding = 'GBK'
    content = get.text.replace('	', '')  # 过滤掉防止json解析出错

    usertext = re.search(r',"__U":(.+?),"__R":', content, flags=re.S).group(1)
    userdict = json.loads(usertext, strict=False)

    replytext = re.search(r',"__R":(.+?),"__T":', content, flags=re.S).group(1)
    replydict = json.loads(replytext, strict=False)

    ttext = re.search(r',"__T":(.+?),"__F":', content, flags=re.S).group(1)
    tdict = json.loads(ttext, strict=False)

    global title
    title = tdict['subject']

    global commentreply
    for i in range(len(replydict)):
        one = ''
        if 'comment' in replydict[str(i)]:  # 该楼层下挂有评论，先+comment，下面到正经楼层
            for one in replydict[str(i)]['comment']:
                commentreply.append([int(replydict[str(i)]['comment'][one]['pid']), replydict[str(i)]['comment'][one]['postdate'], userdict[str(
                    replydict[str(i)]['comment'][one]['authorid'])]['username'], '[评论] ' + str(replydict[str(i)]['comment'][one]['content']), int(replydict[str(i)]['comment'][one]['score'])])

        if 'content' in replydict[str(i)]:  # 正经楼层
            commentnumtxt = ''
            if one != '':
                commentnumtxt = '[评论数:' + str(int(one) + 1) + ']\n\n'
            totalfloor.append([int(replydict[str(i)]['lou']), int(replydict[str(i)]['pid']), replydict[str(i)]['postdate'], userdict[str(
                replydict[str(i)]['authorid'])]['username'], commentnumtxt + str(replydict[str(i)]['content']), int(replydict[str(i)]['score'])])
        else:  # 评论楼层，无content
            for one in commentreply:
                if one[0] == int(replydict[str(i)]['pid']):
                    totalfloor.append([int(replydict[str(i)]['lou']), int(
                        replydict[str(i)]['pid']), one[1], one[2], one[3], one[4]])
                    commentreply.remove(one)

    return int(tdict['replies']) > totalfloor[len(totalfloor)-1][0] and not(len(totalfloor) == 1 and totalfloor[0][0] == 0) # lastposter 对不上 “且”不是只有主楼的情况


def makefile():
    global localmaxfloor
    lastfloor = 0
    total = totalfloor[len(totalfloor)-1][0]
    with open(('./%s/post.md' % name), 'a', encoding='utf-8') as f:
        for onefloor in totalfloor:
            if localmaxfloor < int(onefloor[0]):
                if onefloor[0] == 0:
                    f.write(
                        '### %s\n\n(c) ludoux [GitHub Repo](https://github.com/ludoux/ngapost2md)\n\n' % title)

                f.write("----\n##### %d.[%d] \<pid:%d\> %s by %s\n" %
                        (onefloor[0], onefloor[5], onefloor[1], onefloor[2], onefloor[3]))
                raw = str(onefloor[4])
                #0:楼层；1:pid（不知道是干什么用的）；2:时间；3：发言人；4:内容；5：赞数
                raw = raw.replace('<br/>', '\n')  # 换行
                raw = raw.replace('<br>', '\n')

                rex = re.findall(r'(?<=\[img\]).+?(?=\[/img\])', raw)  # 图片
                for ritem in rex:
                    url = str(ritem)
                    if url[0:2] == './':
                        url = 'https://img.nga.178.com/attachments/' + url[2:]
                    url = url.replace('.medium.jpg', '')
                    filename = hashlib.md5(
                        bytes(url, encoding='utf-8')).hexdigest()[2:8] + url[-6:]
                    if os.path.exists('./%s/%s' % (name, filename)) == False:
                        down(url, ('./%s/%s' % (name, filename)))
                        print('down:./%d/%s [%d/%d]' % (tid, filename, onefloor[0], total))
                    raw = raw.replace(('[img]%s[/img]' %
                                       ritem), ('![img](./%s)' % filename))

                rex = re.findall(r'\[s\:(a2|ac)\:(.+?)\]', raw)  # 表情
                for ritem in rex:
                    raw = raw.replace('[s:%s:%s]' % (
                        ritem[0], ritem[1]), '![%s](../smile/%s.png)' % (ritem[0]+ritem[1], ritem[0]+ritem[1]))
                #[0]人名 [1]时间 [2]圈的内容
                # 引用 [quote][tid=0000000]Topic[/tid] [b]Post by [uid=000000]whowhowho[/uid] (2020-03-26 01:07):[/b]
                rex = re.findall(
                    r'\[quote\].+?\[uid=\d+\](.+?)\[/uid\] \((.+?)\)\:\[/b\](.+?)\[/quote\]', raw, flags=re.S)
                for ritem in rex:
                    quotetext = ritem[2]
                    quotetext = quotetext.replace('\n', '\n>')
                    raw = raw.replace(re.search(r'\[quote\].+?\[uid=\d+\](.+?)\[/uid\] \((.+?)\)\:\[/b\](.+?)\[/quote\]',
                                                raw, flags=re.S).group(), '>%s(%s) said:%s\n' % (ritem[0], ritem[1], quotetext))

                f.write(("%s\n\n" % raw))
                lastfloor = int(onefloor[0])
    return lastfloor


def down(url, path):
    global errortext
    try:
        with closing(requests.get(url, stream=True)) as response:
            chunk_size = 1024  # 单次请求最大值
            with open(path, "wb") as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
    except:
        print('Failed to down url:%s, path:%s' % (url, path))
        errortext = errortext + '<Failed to down url:%s, path:%s>' % (url, path)

def get_title(tid):
    params = (
        ('tid', tid),
        ('_ff', '-7'),
        ('page', 1)
    )
    ss1 = requests.Session()
    get = ss1.get('https://bbs.nga.cn/read.php', headers=headers,
                  params=params, cookies=cookies)
    get.encoding = 'GBK'
    content = get.text
    ##global title
    title = re.search(r'<title>(.+?)</title>', content, flags=re.S).group(1)
    return title

def main():
    global tid
    tid = int(input('tid:'))
    #global target
    global name
    name = get_title(tid).replace(' NGA玩家社区','%s' %str(tid))
    #target=get_title(tid)[0:title_cut]
    holder()
    input('press to exit.')


def holder():
    global localmaxpage
    global localmaxfloor
    global errortext
    print(tid)
    path=os.getcwd()
    #upath=unicode(path,'utf-8')
    dirs=os.listdir(path)
    flag_existence=0
    for filenames in dirs:
        #ufilenames=unicode(filenames,'utf-8')
        if filenames.endswith('%s' % tid):
            flag_existence=1
            if filenames!=name:
                os.rename(filenames,name)
            break
    if flag_existence==0:#not os.path.exists('./%s' % name):#
        os.mkdir(('./%s' % name))
    elif os.path.exists('./%s/max.txt' % name):
        with open('./%s/max.txt' % name, 'r', encoding='utf-8') as f:
            r = f.read()
            localmaxpage = int(r.split()[0])
            localmaxfloor = int(r.split()[1])

    print('localmaxpage%d\nlocalmaxfloor%d' % (localmaxpage, localmaxfloor))
    cpage = localmaxpage
    while single(cpage) != False:
        time.sleep(0.1)
        cpage = cpage + 1

    with open(('./%s/max.txt' % name), 'w', encoding='utf-8') as f:
        f.write("%d %s" % (cpage, totalfloor[len(totalfloor) - 1][0]))

    if os.path.exists('./%s/info.txt' % name):
        with open(('./%s/info.txt' % name), 'a', encoding='utf-8') as f:
            f.write('[%s]%d %s\n' % (time.asctime(
                time.localtime(time.time())), len(totalfloor), errortext))
    else:
        with open(('./%s/info.txt' % name), 'w', encoding='utf-8') as f:
            f.write(
                'tid:%d\ntitle:%s\n(c) ludoux https://github.com/ludoux/ngapost2md\n==========\n' % (tid, title))
            f.write(
                ('[%s]%d %s\n' % (time.asctime(time.localtime(time.time())), len(totalfloor), errortext)))

    print('makeuntil:%d' % makefile())


if __name__ == '__main__':
    main()
