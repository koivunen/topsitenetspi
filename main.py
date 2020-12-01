#!/usr/bin/env python
from bs4 import BeautifulSoup as bs
import itertools
import requests
import sys,os,time
import selenium
import sys
from math import ceil
from pprint import pprint
from pathlib import Path
from joblib import Parallel, delayed
from joblib import Memory
memory = Memory(".joblib", verbose=0)

# TODO: https://github.com/paulirish/headless-cat-n-mouse

import datetime
url_alexa='https://www.alexa.com/topsites/countries/%s'


FI_DOMAINS=Path("top50fi.csv").read_text().splitlines()

#@cachier(cache_dir="./.cachier",stale_after=datetime.timedelta(days=33))
@memory.cache
def gettop(country_code):
   country_code = country_code.upper()

   # garbage from alexa
   if country_code == "FI":
      return [(domain,rank+1,) for rank,domain in enumerate(FI_DOMAINS)]
   
   assert False,"todo"

   response = requests.get(url_alexa % (country_code,))  

   soup = bs(response.text,features="html.parser")
   
   rows = soup.find_all('div', {'class':'site-listing'})

   for row in rows:
     items = row.find_all('div', {'class':'td'})
     site = items[1].a.get_text().strip().lower()
     rank = items[0].get_text().strip()
     #yield (site,rank,)


from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

#@cachier(cache_dir="./.cachier",stale_after=datetime.timedelta(days=3))
@memory.cache
def get_perf_log_on_load(url, headless = True, filter = None):
   try:
      # init Chrome driver (Selenium)
      options = Options()
      options.headless = headless
      options.add_experimental_option('w3c', False)
      cap = DesiredCapabilities.CHROME
      cap['loggingPrefs'] = {'performance': 'ALL'}
      driver = webdriver.Chrome(desired_capabilities = cap, options = options)

      driver.get(url)
      time.sleep(0.5)
      driver.execute_script(Path("cookiebanner-go-away.user.js").read_text())
      time.sleep(0.5)
      
      
      #links = driver.find_elements_by_partial_link_text('')
      #l = links[randint(0, len(links)-1)]
      #l.click()

      if filter: log = [item for item in driver.get_log('performance')
               if filter in str(item)]
      else: log = driver.get_log('performance')
      driver.close()

      return log
   except selenium.common.exceptions.WebDriverException:
      return False

import json
def getUrls(log):
   for msg in log:
     try:
       url=json.loads(msg["message"])["message"]["params"]["request"]["url"]
       yield url
     except KeyError:
       pass

import tldextract

def getConnectedDomains(url):
   log=get_perf_log_on_load(url,headless=True)
   if not log:
      return ["selenium-error.info"]

   domains=[]
   for url in getUrls(log):
     domain = tldextract.extract(url)
     if domain.registered_domain not in domains:
       domains.append(domain.registered_domain)
   return domains


def processDomain(d):
   domains=getConnectedDomains("https://"+d)
   if "" in domains:
      domains.remove("")

   if d in domains:
      domains.remove(d)

   with open("results/"+d+".csv","w") as resfile:
      for domain in domains:
         resfile.write(domain+"\n")

   row=[d]+domains
   return row
   
import json

results = Parallel(n_jobs=3)(delayed(processDomain)(website) for (website,rank) in gettop("fi")[:50])

import graphviz
nodes=[]
dot = graphviz.Digraph(comment='Domain dependencies')
for data in results:
   for idx,domain in enumerate(data):
     if domain not in nodes:
      nodes.append(domain)
      if idx==0:
         dot.node(domain, domain, fillcolor='#ffccaabb',style="filled") 
      else:
         dot.node(domain, domain)

for data in results:
   for domain in data[1:]:
     dot.edge(data[0], domain)

dot.render('output.dot', view=True)

import code
code.interact(local=locals())
