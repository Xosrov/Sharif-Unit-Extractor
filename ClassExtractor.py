#file management
import os
#basic parsing
import re
#advanced parsing
from bs4 import BeautifulSoup
#GET and POST handling
import requests
#others
from datetime import datetime
import json
import argparse

#remove unsafe warnings cause the site has no reliable SSL
from urllib3 import disable_warnings as disUr, exceptions as disUx
disUr(disUx.InsecureRequestWarning)

#file names:
fileDir = os.path.dirname(os.path.realpath(__file__))
htmlInfoFile = os.path.join(fileDir, "Classes.html")
jsonInfoFile = os.path.join(fileDir, "Classes.json")
captchaFile = os.path.join(fileDir, "Captcha.jpg")

#class
class Extractor:
    def __init__(self, username, password):
        #generic user agent to avoid suspicion
        self.user = username
        self.pwd = password
        self.agent = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
        self.session = requests.Session()
        self.loginHeaders = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "max-age=0",
            "upgrade-insecure-requests": "1",
            "user-agent": self.agent
        }
        self.postLoginHeaders = {  # may be redundant, but using anyway
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9,fa-IR;q=0.8,fa;q=0.7,de;q=0.6",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://edu.sharif.edu",
            "referer": "https://edu.sharif.edu/action.do",
            "upgrade-insecure-requests": "1",
            "user-agent": self.agent
        }

    def login(self):
        """
            Login to site using given credentials
            This version requires manual Captcha input
        """
        loginData = {
            "username": self.user,
            "password": self.pwd,
            "jcaptcha": "",
            "command": "login",
            "x": "166",
            "y": "15",
            "captcha_key_name": "",
            "captchaStatus": ""
        }
        loginPage = self.session.get("https://edu.sharif.edu/",
                                     headers=self.loginHeaders, verify=False)
        # extract image and hidden data parameters 
        imgsrc = re.search(r'td><img src="(.*?)"',
                           loginPage.content.decode('utf-8')).group(1)
        hidden = re.search(r'key_name" value="(.*)">.*value="(.*)"',
                           loginPage.content.decode('utf-8'), flags=re.DOTALL)
        loginData["captcha_key_name"] = hidden.group(1)
        loginData["captchaStatus"] = hidden.group(2)
        imageURL = self.session.get("https://edu.sharif.edu/" +
                                    imgsrc, headers=self.loginHeaders, stream=True, verify=False)
        # save captcha to file
        with open(captchaFile, 'wb') as f:
            f.write(imageURL.content)  
        try:
            capt = input(f"Captcha saved to {captchaFile}\nRead and input it: ")
            loginData["jcaptcha"] = capt
            loggedInPage = self.session.post("https://edu.sharif.edu/login.do",
                                            headers=self.loginHeaders, data=loginData, verify=False)
            # with open("test.html", 'w') as f:
            #     f.write(loggedInPage.text)
            # error handling
            if 'font color="red' in loggedInPage.text:
                print("Incorrect Captcha")
                return False
            error = re.search(r'خطای زیر.*\n(.*)', loggedInPage.text)
            if error:
                print("Error: " + error.group(1))
                return False
            return True
        except KeyboardInterrupt:
            print("\nExiting")
            return False
        finally:
            os.remove(captchaFile)

    # NOTE: need to be logged into session for this to work
    def extractVahedInfo(self):
        """
            Extracts and saves data in html and json formats
        """
        data = {
            "changeMenu": "OnlineRegistration*OfficalLessonListShow",
            "isShowMenu": "",
            "commandMessage": "",
            "defaultCss": ""
        }
        vahedSection = self.session.post(
            "https://edu.sharif.edu/action.do", headers=self.postLoginHeaders, data=data, verify=False)
        options = re.findall(r"option value='(\w*)'\s*>(.*?)<",
                             vahedSection.content.decode('utf-8'))
        # basic version of data, used later to craft into dict variant
        dataList = []
        # data names for final json output. values appended to dataList later
        names = ["Campus", "Code", "Group", "Units", "Name", "Reqs", "Capacity", "Count", "Instructor", "Exam date", "Schedule", "Notes1", "Notes2"]
        # POST data
        data = {
            "level": "1",
            "teacher_name": "",
            "sort_item": "1",
            "depID": ""
        }
        print("Saving data in HTML and JSON formats, this may take a while..")
        # html head data
        headData = """<html dir="rtl">\n\n<head>\n  <link rel="icon" href="./favicon.png">\n  <meta name="keywords" content="xosrov, Sharif, vahed, واحد , انتخاب واحد, همه دروس" />\n  <meta name="description" content="List of all classes Sharif UT" />\n  <meta name="viewport" content="width=device-width, initial-scale=1" />\n  <title> لیست تمامی دروس ارایه شده دانشکده های دانشگاه شریف در ترم جاری </title>\n  <style>\n    td {\n      margin-right: 10px;\n      margin-left: 10px;\n\n    }\n\n    .contentTable {\n      background-color: rgb(57, 59, 180);\n      border: 3px dashed red;\n\n    }\n\n    .contentCell {\n      background-color: rgb(238, 238, 238);\n      font-size: 16px;\n      text-align: center;\n\n    }\n\n    .header {\n      background-color: rgb(49, 52, 207);\n      color: white;\n      border: 0.0pt Black;\n      font-size: 18px;\n      text-align: center;\n      font-weight: bold;\n\n    }\n\n    h1.main {\n      font-size: 30px;\n      text-align: center;\n      color: darkgreen;\n\n    }\n\n    h2.date {\n      font-size: 15px;\n      text-align: center;\n      color: black;\n      background: rgba(216, 72, 72, 0.685);\n\n    }\n\n    h1.vahed {\n      font-size: 50px;\n      text-align: center;\n      color: darkgoldenrod;\n      text-decoration: underline;\n\n    }\n\n    hr.small {\n      border: 1px solid black;\n\n    }\n\n    hr.big {\n      border: 5px dotted yellow;\n\n    }\n  </style>\n</head>\n<h1 class="main">لیست تمامی دروس\n</h1>\n<h2 class="date">به روز رسانی شده در """ + \
            str(datetime.now()) + """ </h2>\n<body bgcolor="#e6e6ff">\n"""
        # regex to extract tables
        # TODO: use bs4 here too
        tables = re.compile(r'\s+(<table width.*?table>)', flags=re.DOTALL)
        # file handler that saves into HTML each loop, without needing and memory use
        with open(htmlInfoFile, 'w') as f:
            f.write(headData)
            # loop over list and get data for each campus
            for (id, vahed) in options:
                data["depID"] = id
                chartInfoPage = self.session.post(
                    "https://edu.sharif.edu/action.do", headers=self.postLoginHeaders, data=data, verify=False)
                f.write('<h1 class="vahed">' + vahed + '</h1>')
                for table in re.findall(tables, chartInfoPage.content.decode('utf-8')):
                    # one liner that extracts useful data from each table section and appends them to dataList
                    dataList += [([vahed] + [cell.text.strip() for cell in row("td")]) for row in BeautifulSoup(table, 'lxml')("tr")[2:]]
                    f.write('\n<hr class="small">\n')
                    f.write(table)
                f.write('\n<hr class="big">\n')
            f.write("\n</body>\n</html>")
        print(f"Saved HTML to {htmlInfoFile}")
        # verbose data variable
        dataDict = []
        for each in dataList:
            # zip names and values into dataDict
            dataDict.append(dict(zip(names, each)))
        # save verbose data in json format
        with open(jsonInfoFile, 'w') as f:
            json.dump(dataDict, f, ensure_ascii=False, indent=4)
        print(f"Saved JSON to {jsonInfoFile}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="Username for edu.sharif.edu", required=True)
    parser.add_argument("-p", "--password", help="Password for edu.sharif.edu", required=True)
    args = parser.parse_args()
    extractor = Extractor(args.username, args.password)
    if not extractor.login():
        quit()
    print(f"Logged in as {args.username}")
    extractor.extractVahedInfo()
