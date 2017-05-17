#!/usr/bin/env python
# coding: utf-8 
import json
import time
import re
import sys
import os
import subprocess
import random
import multiprocessing
import platform
import logging
import httplib
import datetime
from collections import defaultdict
from urlparse import urlparse
#from lxml import html
from name_dict import name_dict
from name_dict import name_abbr
from id_group import id_dict
#import pdb

print sys.getdefaultencoding()
reload(sys)   
sys.setdefaultencoding('utf8')
print sys.getdefaultencoding() 


class weLearn:

    def __init__(self):
        self.memberNum = 15
        self.state_in = [0 for i in range(self.memberNum)]
        self.date_time_init = datetime.datetime.now() - datetime.timedelta(2)
        self.time_init_temp = self.date_time_init.strftime('%Y-%m-%d %H:%M')
        self.time_init = datetime.datetime.strptime(self.time_init_temp, '%Y-%m-%d %H:%M')
        self.last_login = [self.time_init for i  in range(self.memberNum)]
        
        self.online_time = [[datetime.timedelta(0) for i in range(self.memberNum)] for i in range(7)]
        self.readStatus()

    def _showMsg(self, message):

        srcName = None
        dstName = None
        groupName = None
        content = None

        msg = message
        logging.debug(msg)

        if msg['raw_msg']:
            srcName = self.getUserRemarkName(msg['raw_msg']['FromUserName'])
            dstName = self.getUserRemarkName(msg['raw_msg']['ToUserName'])
            content = msg['raw_msg']['Content'].replace(
                '&lt;', '<').replace('&gt;', '>')
            message_id = msg['raw_msg']['MsgId']

            if content.find('http://weixin.qq.com/cgi-bin/redirectforward?args=') != -1:
                # 地理位置消息
                data = self._get(content)
                if data == '':
                    return
                data.decode('gbk').encode('utf-8')
                pos = self._searchContent('title', data, 'xml')
                temp = self._get(content)
                if temp == '':
                    return
                tree = html.fromstring(temp)
                url = tree.xpath('//html/body/div/img')[0].attrib['src']

                for item in urlparse(url).query.split('&'):
                    if item.split('=')[0] == 'center':
                        loc = item.split('=')[-1:]

                content = '%s 发送了一个 位置消息 - 我在 [%s](%s) @ %s]' % (
                    srcName, pos, url, loc)

            if msg['raw_msg']['ToUserName'] == 'filehelper':
                # 文件传输助手
                dstName = '文件传输助手'

            if msg['raw_msg']['FromUserName'][:2] == '@@':
                # 接收到来自群的消息
                if ":<br/>" in content:
                    [people, content] = content.split(':<br/>', 1)
                    groupName = srcName
                    srcName = self.getUserRemarkName(people)
                    dstName = 'GROUP'
                else:
                    groupName = srcName
                    srcName = 'SYSTEM'
            elif msg['raw_msg']['ToUserName'][:2] == '@@':
                # 自己发给群的消息
                groupName = dstName
                srcName = self.getUserRemarkName(self.User['UserName'])
                dstName = 'GROUP'

            # 收到了红包
            if content == '收到红包，请在手机上查看':
                msg['message'] = content

            # 指定了消息内容
            if 'message' in msg.keys():
                content = msg['message']

        if groupName != None:
            print '%s |%s| %s -> %s: %s' % (message_id, groupName.strip(), srcName.strip(), dstName.strip(), content.replace('<br/>', '\n'))
            
            if groupName.strip() == "微信机器人测试" or groupName.strip() == "沉迷学习，日渐消瘦":
                print msg['raw_msg']['Content']
                if msg['raw_msg']['FromUserName'][:2] == '@@':
                    self.handleGroupMsg(content, msg['raw_msg']['FromUserName'], srcName)
                elif msg['raw_msg']['ToUserName'][:2] == '@@': 
                    self.handleGroupMsg(content, msg['raw_msg']['ToUserName'], srcName)
#                print mat
#                if mat == True and len(content_new) == 9:
#                    lines = srcName.strip() + '\t' + content_new[0:9] + '\r\n'
#                    print lines
#                    fd = open("test2","a")
#                    fd.write(lines)
#                    fd.close()

            logging.info('%s |%s| %s -> %s: %s' % (message_id, groupName.strip(),
                                                   srcName.strip(), dstName.strip(), content.replace('<br/>', '\n')))
        else:
            print '%s %s -> %s: %s' % (message_id, srcName.strip(), dstName.strip(), content.replace('<br/>', '\n'))
            logging.info('%s %s -> %s: %s' % (message_id, srcName.strip(),
                                              dstName.strip(), content.replace('<br/>', '\n')))

    def handleGroupMsg(self, content, srcName):
        log_info = ''
        content_new = content.replace('<br/>', '\n')
        buffer_content = content.split()
        info = ''
        # query keywords: query or q (for short).
        if buffer_content[0] == "状态" or buffer_content[0].lower() == "state" or buffer_content[0].lower() == "s":
            date_time = datetime.datetime.now()
            name = ''
            if len(buffer_content) == 1:
                name = srcName.decode('UTF-8')
            elif len(buffer_content) == 2 and buffer_conternt[1].isalpha():
                name = buffer_content[1].decode('UTF-8')

            if name_dict.has_key(name):
                check_info = {'name' : name_dict[name]}
                log_info = ''
                return self.checkStatus(check_info)
        elif buffer_content[0] == "查询" or buffer_content[0].lower() == "query" or buffer_content[0].lower() == "q":
            date_time = datetime.datetime.now()
            name = ''
            if len(buffer_content) == 1:
                name = srcName.decode('UTF-8')
            elif len(buffer_content) == 2 and buffer_content[1].isalpha():
                name = buffer_content[1].decode('UTF-8')

            if name_dict.has_key(name):
                info = '[' + date_time.strftime('%Y-%m-%d %H:%M') + ']: ' + name_dict[name] + ' login' 
                check_info = {'name' : name_dict[name], 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
                log_info = ''
                return self.handleCheck(check_info)
            else:
                info = '查无此人'
                log_info = ''
        # Response to "签入/签到" "签出"
        # login keywords: login or in (for short).
        elif content == "签入" or content == "签到" or content.lower() == "login" or content.lower() == "in":
            date_time = datetime.datetime.now()
            print repr(srcName)
            print srcName
            name = srcName.decode('UTF-8')
            if name_dict.has_key(name):
                info = '[' + date_time.strftime('%Y-%m-%d %H:%M') + ']: ' + name_dict[name] + ' login' 
                log_info = {'name' : name_dict[name], 'state' : '1', 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
            else:
                info = '用户未注册'
                log_info = ''
        # logout keywords: logout or out (for short).
        elif content == "签出" or content.lower() == "logout" or content.lower() == "out":
            date_time = datetime.datetime.now()
            name = srcName.decode('UTF-8')
            if name_dict.has_key(name):
                info = '[' + date_time.strftime('%Y-%m-%d %H:%M') + ']: ' + name_dict[name] + ' logout' 
                log_info = {'name' : name_dict[name], 'state' : '0', 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
            else:
                info = "用户未注册"
                log_info = ''
        # sum keywords: sum.
        elif content == "统计" or content.lower() == "sum":
            date_time = datetime.datetime.now()
            name = ''
            if len(buffer_content) == 1:
                name = srcName.decode('UTF-8')
            elif len(buffer_content) == 2 and buffer_content[1].isalpha():
                name = buffer_content[1].decode('UTF-8')

            if name_dict.has_key(name):
                check_info = {'name' : name_dict[name], 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
                return self.timeSum(check_info)
        # thisrank keywords: thisrank.
        elif content == "今日排名" or content == "今日排行" or content.lower() == "thisrank":
            date_time = datetime.datetime.now()
            name = srcName.decode('UTF-8')
            check_info = {'name' : name_dict[name], 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
            return self.thisRank(check_info)
        # rank keywords: rank.
        elif content == "排名" or content == "排行" or content.lower() == "rank":
            date_time = datetime.datetime.now()
            name = srcName.decode('UTF-8')
            check_info = {'name' : name_dict[name], 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
            return self.timeRank(check_info)
        elif content == "读取状态":
            return self.readStatus()
        elif content == "sudo清空重置":
            date_time = datetime.datetime.now()
            fn = 'data/data_' + date_time.strftime('%Y-%m-%d') + '.json'
            fd = open(fn,'w+')
            for i in range(self.memberNum):
                line = (str)(self.state_in[i]) + '\t' + (str)(self.last_login[i])
                for j in range(7):
                    line = line + '\t' + (str)(self.online_time[j][i].total_seconds())
                line = line + '\t'+ 'end' + '\n'
                fd.write(line)
            fd.close()
            for i in range(self.memberNum):
            	self.state_in[i] = 0
            	self.last_login[i] = self.time_init
            	for j in range(7):
            		self.online_time[j][i] = datetime.timedelta(0)
            fd = open('cache','w+')
            for i in range(self.memberNum):
                line = (str)(self.state_in[i]) + '\t' + (str)(self.last_login[i])
                for j in range(7):
                    line = line + '\t' + (str)(self.online_time[j][i].total_seconds())
                line = line + '\t'+ 'end' + '\n'
                fd.write(line)
            fd.close()
            return '重置成功'

        else:
            try:
                if len(buffer_content) == 2 and buffer_content[0].isdigit() and buffer_content[1].isalpha():
                    if len(buffer_content[0]) == 9:
                        time = buffer_content[0][0:8]
                        state = buffer_content[0][8]
                        usr = buffer_content[1]
    
                        date_time = datetime.datetime(datetime.date.today().year, 
                            int(buffer_content[0][0:2]), int(buffer_content[0][2:4]),
                            int(buffer_content[0][4:6]), int(buffer_content[0][6:8]))

                        if state is '1' :
                            if name_dict.has_key(usr):
                                if usr == 'gjq':
                                    date_time = date_time + datetime.timedelta(0, 43200)
                                    info = '[' + date_time.strftime('%Y-%m-%d %H:%M') + ']: ' + name_dict[usr] + ' login' 
                                    log_info = {'name' : name_dict[usr], 'state' : '1', 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
                                else:
                                    info = '[' + date_time.strftime('%Y-%m-%d %H:%M') + ']: ' + name_dict[usr] + ' login' 
                                    log_info = {'name' : name_dict[usr], 'state' : '1', 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
                            else:
                                info = '用户未注册'
                                log_info = ''
                        elif state is '0':
                            if name_dict.has_key(usr):
                                if usr == 'gjq':
                                    date_time = date_time + datetime.timedelta(0, 43200)
                                    info = '[' + date_time.strftime('%Y-%m-%d %H:%M') + ']: ' + name_dict[usr] + ' logout' 
                                    log_info = {'name' : name_dict[usr], 'state' : '0', 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
                                else:
                                    info = '[' + date_time.strftime('%Y-%m-%d %H:%M') + ']: ' + name_dict[usr] + ' logout' 
                                    log_info = {'name' : name_dict[usr], 'state' : '0', 'time' : date_time.strftime('%Y-%m-%d %H:%M')}
                            else:
                                info = '用户未注册'
                                log_info = ''
                        else:
                            info = 'error'
                            log_info = ''
                    else:
                        return '时间格式错误【自动回复】'
                        log_info = ''

            except Exception, e:
                return (str(e) + '【自动回复】')
                log_info = ''
                pass

        try:
            extra_info = ''
            flag = False
            if log_info is not '':
                [extra_info, flag] = self.checkLogInfo(log_info)
                if flag is True:
                    #save data
                    fn = 'data/data_' + date_time.strftime('%Y-%m-%d') + '.json'
                    with open(fn, 'a') as f:
                        f.write(json.dumps(log_info) + '\n')
                    f.close()
                    fd = open('cache','w+')
                    for i in range(self.memberNum):
                        line = (str)(self.state_in[i]) + '\t' + (str)(self.last_login[i])
                        for j in range(7):
                            line = line + '\t' + (str)(self.online_time[j][i].total_seconds())
                        line = line + '\t'+ 'end' + '\n'
                        fd.write(line)
                    fd.close()
                    return (info + '【自动回复】\n' + extra_info)
                else:
                    return extra_info
        except Exception, e:
            print str(e)
            pass

        return ''

#        print log_info
#        if log_info is not '':
#            if flag is True:
#                print 'ok'
#                fn = 'data/data_' + date_time.strftime('%Y-%m-%d') + '.json'
#                with open(fn, 'a') as f:
#                    f.write(json.dumps(log_info) + '\n')
#                f.close()
#                fd = open('cache','w+')
#                for i in range(self.memberNum):
#                    line = (str)(self.state_in[i]) + '\t' + (str)(self.last_login[i])
#                    for j in range(7):
#                        line = line + '\t' + (str)(self.online_time[j][i].total_seconds())
#                    line = line + '\t'+ 'end' + '\n'
#                    fd.write(line)
#                fd.close()

    def readStatus(self):
        fd = open('cache','r')
        num = 0
        for lines in fd.readlines():
            content_all = lines.split('\t')
            
            self.state_in[num] = (int)(content_all[0])
            self.last_login[num] = datetime.datetime.strptime(content_all[1], '%Y-%m-%d %H:%M:%S')
            for i in range(7):
                print(content_all[2+i])
                print((str)(i))
                temp_time = content_all[2+i][:-2]
                self.online_time[i][num] = datetime.timedelta(0,(int)(temp_time))
            num = num + 1
        return '读取成功'

    def checkStatus(self, check_info):
        name = check_info['name']
        id = int(id_dict[name])
        
        if self.state_in[id] is 0:
            info = name + '当前状态：离线\n'
            last_login_info = '上次登出时间：' + self.last_login[id].strftime('%Y-%m-%d %H:%M:%S')
            return info + last_login_info
        elif self.state_in[id] is 1:
            info = name + '当前状态：在线\n'
            last_login_info = '上次登录时间：' + self.last_login[id].strftime('%Y-%m-%d %H:%M:%S')
            return info + last_login_info
    def checkLogInfo(self, log_info):
        action = int(log_info['state']) #'0': logout, '1': login
        name = log_info['name']
        id = int(id_dict[name])
        time = datetime.datetime.strptime(log_info['time'], '%Y-%m-%d %H:%M')
        info = ''
        flag = False

        if self.state_in[id] is 0 and action is 0:
            info = '【签出失败】您尚未登入'
            return [info, flag]
        elif self.state_in[id] is 1 and action is 1:
            info = '【签到失败】您尚未登出'
            return [info, flag]
        elif self.state_in[id] is 0 and action is 1:
            if self.last_login[id] > time:
                info = '【签到失败】签入时间在签出时间之前'
            elif time - datetime.datetime.now() >= datetime.timedelta(0, 3600): #登入时间超出当前时间一小时
                info = '【签到失败】签入时间超出当前时间1小时'
            else:
                self.last_login[id] = time
                self.state_in[id] = 1
                weekday = time.weekday()
                if self.online_time[weekday][id] == datetime.timedelta(0):
                    info = '夏天来了，期末还会远吗~您刚开始沉迷学习，加油'
                else:
                    info = '您今日沉迷学习时间为：' + str(self.online_time[weekday][id])
                flag = True
            return [info, flag]
        elif self.state_in[id] is 1 and action is 0:
            if self.last_login[id] > time:
                info = '【签出失败】签出时间在签入时间之前'
            elif time - datetime.datetime.now() >= datetime.timedelta(0, 3600):
                info = '【签出失败】签出时间超出当前时间1小时'
            else:
                self.state_in[id] = 0
                duration = time - self.last_login[id]
                weekday = time.weekday()
                self.online_time[weekday][id] = self.online_time[weekday][id] + duration
                #online_time_sum[id] = online_time_sum[id] + duration
                info = '本次学习时间为：' + str(duration) + '\n今日沉迷学习时间为：' + str(self.online_time[weekday][id])
                flag = True
            return [info, flag]

    def handleCheck(self, check_info):
        name = check_info['name']
        id = int(id_dict[name])
        time = datetime.datetime.strptime(check_info['time'], '%Y-%m-%d %H:%M')

        duration = (time - self.last_login[id]) * self.state_in[id]
#        if self.state_in[id] is 1:
#            duration = time - self.last_login[id]
#        else:
#            duration = datetime.timedelta(0)

        weekday = time.weekday()
        online_time_curr = self.online_time[weekday][id] + duration
        #rank = self.memberNum + 1

        #for i in range(self.memberNum):
        #    if online_time_curr >= online_time[weekday][i] + (time - self.last_login[i]) * self.state_in[i]:
        #        rank = rank - 1
        #msg = name + '今日在线总时间为：' + str(online_time_curr) + '\n排名第' + str(rank) + '位'
        msg = name + '今日在线总时间为：' + str(online_time_curr)
        return msg

    def timeSum(self, check_info):
        name = check_info['name']
        id = int(id_dict[name])
        time = datetime.datetime.strptime(check_info['time'], '%Y-%m-%d %H:%M')

        duration = (time - self.last_login[id]) * self.state_in[id]
#        if self.state_in[id] is 1:
#            duration = time - self.last_login[id]
#        else:
#            duration = datetime.timedelta(0)

        weekday = time.weekday()
        sum_time = datetime.timedelta(0)
        for i in range(weekday + 1):
            sum_time = sum_time + self.online_time[i][id]
        sum_time = sum_time + duration
        msg = name + '本周在线总时间为：' + str(sum_time)
        return msg

    # [func] ranking for the queryed date
    #        code reused from [func]timeRank
    #        todo: 1. time zone issue of Jacky Gao
    #              2. start time modified as 06:00 am
    def thisRank(self, check_info):
        online_this_sum = [datetime.timedelta(0) for i in range(self.memberNum)]
        thisseconds = [0 for i in range(self.memberNum)] # seconds count for today till queryed time
        name = check_info['name']
        id = int(id_dict[name])
        time = datetime.datetime.strptime(check_info['time'], '%Y-%m-%d %H:%M')
        for i in range(self.memberNum):
            duration = (time - self.last_login[i]) * self.state_in[i]
            weekday = time.weekday()
            online_this_sum[i] = self.online_time[weekday][i] + duration
            thisseconds[i] = online_this_sum[i].total_seconds()
        name_list = ['徐凯源','宋绍铭','刘　洋','韩纪飞','高佳琦','郭东旭','张若冰','韩晓霏','于　超','林声远','鸡器人','厉丹阳','王佳林','韦　洁' ,'陈佳宁']
        name_list_eng = ['xky','ssm','ly','hjf','gjq','gdx','zrb','hxf','yc','lsy','test','ldy','wjl','wj' ,'cjn']
        lists = zip(thisseconds, online_this_sum, name_list, name_list_eng)
        lists.sort(key=lambda x:x[0],reverse=True)
        msg = '今日当前排名：\n'
        rank = 0
        for i in range(self.memberNum):
            rkstr = '  %d' % (i+1)  # rank string
            if len(rkstr) < 4: # add two (half-width) space for alignment
                rkstr = '  ' + rkstr
            hrstr = '%2.1f' % (lists[i][0] / 3600.0) # hour string 
            if len(hrstr) < 4: # add four (half-width) space for alignment
                hrstr = '    ' + hrstr
            elif len(hrstr) < 5: # add two (half-width) space for alignment
                hrstr =   '  ' + hrstr
            msg = msg + rkstr + ' | ' + lists[i][2] + ' ' + hrstr + ' 小时\n'
            if lists[i][3] == name:
                rank = i + 1
        if rank != 0:
            names = lists[rank - 1][2].replace('　', '') # omit the full-width space '\xa1\xa1'
            # splitline = '——————————\n' # split line (caution: display varies with PC and phone)
            msg = msg + names + "的当前排名：" + (str)(rank)
        return msg

    def timeRank(self, check_info):
        online_time_sum = [datetime.timedelta(0) for i in range(self.memberNum)]
        totalseconds = [0 for i in range(self.memberNum)]
        name = check_info['name']
        id = int(id_dict[name])
        time = datetime.datetime.strptime(check_info['time'], '%Y-%m-%d %H:%M')
        for i in range(self.memberNum):
            duration = (time - self.last_login[i]) * self.state_in[i]
            weekday = time.weekday()
            for j in range(weekday + 1):
                online_time_sum[i] = online_time_sum[i] + self.online_time[j][i]
            online_time_sum[i] = online_time_sum[i] + duration
            totalseconds[i] = online_time_sum[i].total_seconds()
        name_list = ['徐凯源','宋绍铭','刘　洋','韩纪飞','高佳琦','郭东旭','张若冰','韩晓霏','于　超','林声远','鸡器人','厉丹阳','王佳林','韦　洁' ,'陈佳宁']
        name_list_eng = ['xky','ssm','ly','hjf','gjq','gdx','zrb','hxf','yc','lsy','test','ldy','wjl','wj' ,'cjn']
        lists = zip(totalseconds, online_time_sum, name_list, name_list_eng)
        lists.sort(key=lambda x:x[0],reverse=True)
        msg = '本周目前排名：\n'
        rank = 0
        for i in range(self.memberNum):
            rkstr = '  %d' % (i+1)  # rank string
            if len(rkstr) < 4: # add two (half-width) space for alignment
                rkstr = '  ' + rkstr
            hrstr = '%2.1f' % (lists[i][0] / 3600.0) # hour string 
            if len(hrstr) < 4: # add four (half-width) space for alignment
                hrstr = '    ' + hrstr
            elif len(hrstr) < 5: # add two (half-width) space for alignment
                hrstr =   '  ' + hrstr
            msg = msg + rkstr + ' | ' + lists[i][2] + ' ' + hrstr + ' 小时\n'
            if lists[i][3] == name:
                rank = i + 1
        if rank != 0:
            names = lists[rank - 1][2].replace('　', '') # omit the full-width space '\xa1\xa1'
            # splitline = '——————————\n' # split line (caution: display varies with PC and phone)
            msg = msg + names + "的目前排名：" + (str)(rank)
        return msg
