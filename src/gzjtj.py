
import os
from typing import Text
from pdfminer.layout import TextGroupElement
import pdfplumber
import requests
from bs4 import BeautifulSoup
import zipfile
import rarfile
import shutil


class NewsUrl:
    def __init__(self, date, text, href):
        self.date = date
        self.text = text
        self.href = href


def fileUrlList(firstUrl,url_list):
    response = requests.get(firstUrl)
    if response.status_code != 200 :
        print ("connection exception")
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text,"html.parser")

    #内容列表
    news_list = soup.body.find('div', class_='blist').find_all('dd')
    for news in  news_list:
        a = news.find('a')
        date = news.find('span').text
        if a.text.find('摇号')>-1 and a.text.find('配置结果')>-1:
            newsUrl = NewsUrl(date,a.text,a.attrs['href'])
            url_list.append(newsUrl)
        if date.find('2018-07') >-1 and a.text.find('指标配置结果')>-1 and a.text.find('情况表')<0 and a.text.find('2018年1月')<0:
            newsUrl = NewsUrl(date,a.text,a.attrs['href'])
            url_list.append(newsUrl)
    #下一页
    li_next_a = soup.body.find('div',class_='pageturn').find('li',class_='next').find('a')
    if len(li_next_a.attrs)>0 and li_next_a.attrs['href'] != None:
        fileUrlList(li_next_a.attrs['href'],url_list)
    return url_list

def pdfUrl(news_url):
    response = requests.get(news_url)
    if response.status_code != 200 :
        print ("connection exception")
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text,"html.parser")

    #内容列表
    pdf_list = soup.body.find('div', class_='details').find_all('a')
    for pdf_item in  pdf_list:
        downfile(pdf_item.attrs['href'])

    return len(pdf_list)

def downfile(file_url):
    currentPath = os.path.dirname(os.getcwd())
    file_name = os.path.basename(file_url)    
    f_path = currentPath + '\\resource\\' + file_name
    if os.path.isfile(f_path):
        print ('"%s"file is exist' % (file_name))
    else:
        r = requests.get(file_url, stream=True)    
        with open(f_path, "wb") as pdf:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    pdf.write(chunk)
        print ('"%s" download succeed' % (file_name))

def searchFilesUnzip(path,*args):
    for root, dirs, files in os.walk(path):  # path 为根目录
        for file_name in files:
            for arg in args:
                if file_name.find(arg)>-1:
                    if arg=='zip':
                        zip_file = zipfile.ZipFile(path+'\\'+file_name)
                        zip_list = zip_file.namelist() # 得到压缩包里所有文件
                        for f in zip_list:
                            zip_file.extract(f, path) # 循环解压文件到指定目录 
                        zip_file.close() # 关闭文件，必须有，释放内存
                    elif arg=='rar':
                        rf = rarfile.RarFile(path+'\\'+file_name, mode='r') # mode的值只能为'r'
                        rf_list = rf.namelist() # 得到压缩包里所有的文件
                        for f in rf_list:        
                            rf.extract(f, path)  # 循环解压，将文件解压到指定路径
                        rf.close()

def printpdf(f_path):
    currentPath = os.path.dirname(os.getcwd())
    out_path = currentPath +'\\yield\\result.json'

    firstFlagStr = '序号         申请编码         姓名\n'    
    firstLen = len(firstFlagStr)
    pageFormat = '-%d-'
    lastFlagStr = '\n      -中签详细列表数据完成-\n'
    ballotDateFlagStr='分期编号：'
    personFlagStr='个人'
    energyFlagStr='节能'
    ballotDateFlagStr='分期编号：'
    rowFormat = '{"ballot_code":"%s","user_name":"%s","ballot_type":%d,"ballot_date":"%s"}'
    ballot_date =''
    ballot_type = 1 # 1个人普通；2个人节能；3单位普通；4单位节能
    counter = 0
    result = '时间：%s 人数：%d 类型：%s 文件：%s'

    with pdfplumber.open(f_path) as pdf, open(out_path ,'a') as txt:        
        pagestr = ''
        for page in pdf.pages:
            textdata = page.extract_text()
            if page.page_number ==1:
                if textdata.find(personFlagStr) >-1:
                    if textdata.find(energyFlagStr) >-1:
                        ballot_type=2
                else:
                    return (False,'单位：'+f_path)
                    firstFlagStr = '序号         申请编码         名称\n' # 公司
                    if textdata.find(energyFlagStr) >-1:
                        ballot_type=4
                    else:
                        ballot_type=3
                ballotDateIndex = textdata.find(ballotDateFlagStr)
                if ballotDateIndex > -1 :
                    start_index = ballotDateIndex+len(ballotDateFlagStr)
                    end_index =start_index+6
                    ballot_date = textdata[start_index:end_index]

                firstIndex = textdata.find(firstFlagStr)
                if firstIndex > -1 :
                    textdata = textdata[firstIndex+firstLen:]

            textdata = textdata.replace(pageFormat % (page.page_number),'')
            lastIndex = textdata.find(lastFlagStr)
            if lastIndex > -1 :
                textdata = textdata[:lastIndex]
            textdata = textdata.rstrip()
            list = textdata.split('\n')
            for item in list:
                row = item.lstrip()
                column = row.split('      ')
                if len(column)==3 and column[1].isdigit():
                    rowStr = rowFormat % (column[1],column[2],ballot_type,ballot_date)
                    #print (rowStr)
                    pagestr = pagestr + (rowStr+'\n')
                    counter+=1
                else:
                    return (False,f_path)

        txt.write(pagestr)

    ballot_typeStr = '个人普通'
    if ballot_type==2:
        ballot_typeStr = '个人节能'
    elif ballot_type==3:
        ballot_typeStr = '单位普通'
    elif ballot_type==4:
        ballot_typeStr = '单位节能'
    resultStr = (result % (ballot_date,counter,ballot_typeStr,f_path))
    print (resultStr)
    return (True,resultStr)

print ('begin')

#------step1------下载全部摇号结果文章地址-并存到txt
def downfileUrl():
    news_list = []
    news_list = fileUrlList('https://jtzl.jtj.gz.gov.cn/index/gbl/',news_list)
    currentPath = os.path.dirname(os.getcwd())
    file_name = 'pdf_url_resource'
    url_file_path = currentPath + '\\resource_url\\' + file_name +'.txt'
    url_remark_file_path = currentPath + '\\resource_url\\' + file_name +'_remark.txt'
    url_file = open(url_file_path, "w") #只写并创建
    url_remark_file = open(url_remark_file_path, "w") #只写并创建
    for news in news_list:
        url_remark_file.write('时间：%s 标题：%s 地址：%s \n' % (news.date,news.text,news.href))
        url_file.write('%s\n' % (news.href))
    url_remark_file.close()
    url_file.close()
#step1：please run downfileUrl
#downfileUrl()

#------step2------读取摇号结果文章地址-并下载pdf
def downfilePdf():
    file_name = 'pdf_url_resource'
    currentPath = os.path.dirname(os.getcwd())
    url_file_path = currentPath + '\\resource_url\\' + file_name +'.txt'
    url_file = open(url_file_path, "r") #只写并创建
    urlstr = url_file.read(-1)
    url_file.close()

    url_down_result_file_path = currentPath + '\\resource_url\\' + file_name +'_result.txt'
    url_down_result_file = open(url_down_result_file_path, "w") #只写并创建    

    urlstr = urlstr.rstrip()
    list = urlstr.split('\n')
    for item in list:
        pdf_count = pdfUrl(item)
        url_down_result_file.write('url：%s pdf数量：%d\n' % (item,pdf_count))

    url_down_result_file.close()
#step2：please run downfilePdf
#downfilePdf()

#------step3------解压zip和rar
def unzipfile():
    currentPath = os.path.dirname(os.getcwd())
    f_path = currentPath + '\\resource'
    searchFilesUnzip(f_path,'zip','rar')
#step3：please run unzipfile
#unzipfile()

#------step4------解析pdf
def analypdf(f_path):
    currentPath = os.path.dirname(os.getcwd())
    result_ramark_path = currentPath +'\\yield\\result_ramark.txt'    
    result_error_path = currentPath +'\\yield\\result_error.txt' 
    for root, dirs, files in os.walk(f_path):
        for file_name in files:
            if file_name.find('pdf') >-1:                
                file_path = f_path+'\\'+file_name                
                result_ramark = open(result_ramark_path, "a+") 
                result_error = open(result_error_path, "a+") 
                result_ramark.seek(0)
                result_error.seek(0)
                result_ramarkStr =  result_ramark.read()
                result_errorStr =  result_error.read()
                if result_ramarkStr.find(file_path)>-1 or result_errorStr.find(file_path)>-1:
                    print ('已经执行：%s'%(file_path))
                else:
                    if os.path.exists(file_path):
                        isOK,resultInfo = printpdf(file_path)
                        if isOK:
                            result_ramark.write('%s\n' % (resultInfo))
                            os.remove(file_path)
                        else:
                            result_error.write('%s\n' % (resultInfo))
                result_ramark.close()
                result_error.close()
        for dir_item in dirs:
            analypdf(f_path+'\\'+dir_item)

def analyallpdf():
    currentPath = os.path.dirname(os.getcwd())
    f_path = currentPath + '\\resource'

    analypdf(f_path)
#step4：please run analyallpdf
#analyallpdf()

#------日常更新------
def everyUpdate(url):
    pdfUrl(url);
    analyallpdf();

# 输入摇号结果地址
everyUpdate('https://jtzl.jtj.gz.gov.cn/index/gbl/20221128/1669606780488_1.html'); 

#name,suffix = downfile('https://jtzl.jtj.gz.gov.cn/attachment/20211227/1640592692103.pdf')
#printpdf(name,suffix)
print ('down finish')