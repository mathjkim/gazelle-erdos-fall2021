#!/usr/bin/env python
# coding: utf-8

import sqlite3
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import time

from urllib.request import Request,urlopen
import re

import nltk
from nltk.tokenize import word_tokenize
from string import punctuation
import string

#Necessary to avoid hangups later with some of the URL reads
header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
          'AppleWebKit/537.11 (KHTML, like Gecko) '
          'Chrome/23.0.1271.64 Safari/537.11',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
          'Accept-Encoding': 'none',
          'Accept-Language': 'en-US,en;q=0.8',
          'Connection': 'keep-alive'}

#How often to re-run the subreddit check sequence
check_timer = 20 #minutes

def warn(*args, **kwargs):
    pass
import warnings
warnings.warn = warn

def rmse(true, prediction):
    return np.sqrt(np.sum(np.power(true-prediction,2))/len(true))

def mean_err(true, prediction):
    return np.sum(true-prediction)/len(true)

def powerset_no_empty(s):
    power_set = []
    x = len(s)
    for i in range(1 << x):
        power_set.append([s[j] for j in range(x) if (i & (1 << j))])
            
    return power_set[1:]

#First fit the best classifier as found by Soudi's analysis, a logistic regression with C=0.1

#connect to the WSB database file and create an associated cursor
conn = sqlite3.connect("reddit_wallstreetbets.db")
c = conn.cursor()

c.execute("SELECT * FROM new_posts")
new_posts_df = pd.DataFrame(c.fetchall(), columns = [x[0] for x in c.description])
#print( 'new_posts now has '+str(len(new_posts_df))+' entries.' )
c.execute("SELECT * FROM post_stats")
post_stats_df = pd.DataFrame(c.fetchall(), columns = [x[0] for x in c.description])
#print( 'post_stats now has '+str(len(post_stats_df))+' entries.' )

incomplete_entries = []
upvotes_24hrs = []
top_hot_loc = []
for i in range(len(new_posts_df)):
    c.execute("SELECT upvotes FROM post_stats where hour=24 and post_id="+str(i))
    fetch_val = c.fetchall()
    if len( fetch_val ) < 1:
        incomplete_entries.append(i)
    else:
        upvotes_24hrs.append( fetch_val[0][0] )
    c.execute("SELECT hot_val FROM post_stats where post_id="+str(i))
    top_hot_loc.append( min(c.fetchall())[0] )

time_vals = []
days = []
for i in range(len(new_posts_df)):
    time_str = new_posts_df["submit_time"][i].split('T')[1]
    time_val = float(time_str.split(':')[0])+float(time_str.split(':')[1])/60.+float(time_str.split(':')[2])/360.
    time_vals.append(time_val)
    days.append( pd.Timestamp( new_posts_df["submit_time"][i].split('T')[0].replace('"','') ).day_name() )

new_posts_df['submit_hour'] = time_vals
new_posts_df['submit_day'] = days
new_posts_df['best_hot_val'] = top_hot_loc

WSB_df = new_posts_df.drop(incomplete_entries)
WSB_df['upvotes_tot'] = upvotes_24hrs

WSB_df['redditor_for'] = WSB_df['redditor_for'] - min(WSB_df['redditor_for'])


#Need a definition of 'viral'
#Let's go with more than 684 upvotes, the mean from our initial study sample
viral = []
for post_id in WSB_df['post_id']:
    if (WSB_df['upvotes_tot'][post_id] >= 684):
        viral.append(1)
    #elif (WSB_df['best_hot_val'][post_id] <= 5):
    #    viral.append(1)
    else:
        viral.append(0)

WSB_df['viral'] = viral

#Get one-hot encoded day and flair variables and add them to the df
WSB_df = pd.concat([WSB_df, pd.get_dummies(WSB_df['flair'])], axis=1)
WSB_df = pd.concat([WSB_df, pd.get_dummies(WSB_df['submit_day'])], axis=1)

#Get simple language statistics
title = WSB_df['title']
symbolset = string.punctuation
n = len(title)
WSB_df["propernouns"] = np.zeros(n)
WSB_df["numbers"] = np.zeros(n)
WSB_df["hashtags"] = np.zeros(n)
WSB_df["symbols"] = np.zeros(n)
for i in title.index:
    text = title[i]
    words = nltk.word_tokenize(text)
    taggedtoken = nltk.pos_tag(words)
    NPcount = 0
    NUMcount = 0
    SYMcount = 0
    HASHcount = 0
    for word in taggedtoken:
        if word[1] == "NNP" or word[1] == "NNPS":
            NPcount += 1
        if word[1] == "JJ" or word[1] == "CD":
            NUMcount += 1
        if word[0] == "#":
            HASHcount += 1
        if word[0] in symbolset :
            SYMcount += 1
    WSB_df["propernouns"][i] = NPcount
    WSB_df["numbers"][i] = NUMcount
    WSB_df["hashtags"][i] = HASHcount
    WSB_df["symbols"][i] = SYMcount

##Do an 80/20 train/test split
#WSB_df_train, WSB_df_test = train_test_split(WSB_df, shuffle=True, random_state=48, test_size=.2)

#Use the subset of features Soudi selected from her analysis
selected_features = ['hot_val','upvotes','DD','Daily Discussion','Discussion','Gain','Loss','Meme',
       'Mods','News','Technical Analysis','Weekend Discussion','YOLO']

#Fit the logistic regression model
#log_reg_clf = LogisticRegression(C = 0.1, max_iter = 10000)
#log_reg_clf.fit(WSB_df_train[selected_features], WSB_df_train['viral'])
#pred = log_reg_clf.predict(WSB_df_test[selected_features])
#acc_val = accuracy_score(WSB_df_test['viral'], pred)
#print(acc_val)

log_reg_clf = LogisticRegression(C = 0.1, max_iter = 10000)
log_reg_clf.fit(WSB_df[selected_features], WSB_df['viral'])



#Keep track of previously checked URLs to avoid repetition
#and replicate the data collection method as much as possible
checked_urls = []

def check_iterator():
    def new_post_entry(url_str):
        #This runs for each post being newly recorded
        print("Looking at new post: "+url_str)

        req = Request(url=url_str,headers=header)
        sourceCode = urlopen(req).read().decode()
        time.sleep(1)

        if (not '<span class="promoted-tag">' in sourceCode) and (not '?promoted=1' in url_str):
            #this skips promoted posts
            active_track = 'Yes'
            title = re.findall('property="og:title" content="(.*?)">',sourceCode)[0].replace("'","")
            comment_url = url_str
            if 'self.wallstreetbets' in sourceCode:
                link_url = comment_url
                # ^this deals with self-posts
            else:
                link_url = re.findall('"target_url": "(.*?)",',sourceCode)[0]
            if 'linkflairlabel' in sourceCode:
                flair = re.findall('<span class="linkflairlabel " title="(.*?)">',sourceCode)[0]
            else:
                flair = 'None'
            submit_time = re.findall('<span>this post was submitted on &#32;</span><time datetime=(.*?)">',sourceCode)[0].replace('+00:00','')
            if comment_url in rising_urls:
                rising_val = rising_urls.index(comment_url)
            else:
                rising_val = 99
            if comment_url in hot_urls:
                hot_val = hot_urls.index(comment_url)
            else:
                hot_val = 999

            if 'Posted in r/wallstreetbets' in sourceCode:
                username = re.findall('property="og:description" content="Posted in r/wallstreetbets by u/(.*?) ',sourceCode)[0]
            else:
                username = re.findall('<a href="https://old.reddit.com/user/(.*?)" class',sourceCode)[0]
                # ^this deals with self-posts
            usr_req = Request(url='https://www.reddit.com/user/'+username+'/about.json',headers=header)
            usr_sourceCode = urlopen(usr_req).read().decode()
            time.sleep(1)

            post_karma = re.findall('"link_karma": (.*?),',usr_sourceCode)[0]
            comment_karma = re.findall('"comment_karma": (.*?),',usr_sourceCode)[0]
            creation_date = re.findall('"created_utc": (.*?),',usr_sourceCode)[0]
            redditor_for =  (float(time.time()) - float(creation_date)) / 86400.0 #days

            upvotes = re.findall('<div class="score"><span class="number">(.*?)</span>', sourceCode)[0]
            upvote_percent = re.findall('span>&#32;\((.*?)% upvoted', sourceCode)[0]
            if '<span class="title">no comments (yet)</span>' in sourceCode:
                num_comments = 0
            else:
                num_comments = re.findall('class="bylink comments may-blank" rel="nofollow" >(.*?) comment', sourceCode)[0]

            DD,DailyDisc,Disc,Gain,Loss,Meme,Mods,News,TA,WD,YOLO,fNone = 0,0,0,0,0,0,0,0,0,0,0,0
            if 'flair' == 'DD':
                DD = 1
            elif 'flair' == 'Daily Discussion':
                DailyDisc = 1
            elif 'flair' == 'Discussion':
                Disc = 1
            elif 'flair' == 'Gain':
                Gain = 1
            elif 'flair' == 'Loss':
                Loss = 1
            elif 'flair' == 'Meme':
                Meme = 1
            elif 'flair' == 'Mods':
                Mods = 1
            elif 'flair' == 'News':
                News = 1
            elif 'flair' == 'Technical Analysis':
                TA = 1
            elif 'flair' == 'Weekend Discussion':
                WD = 1
            elif 'flair' == 'YOLO':
                YOLO = 1
            else:
                fNone = 1

            page_stats_df = pd.DataFrame([[hot_val,upvotes,DD,DailyDisc,Disc,Gain,Loss,Meme,Mods,News,TA,WD,YOLO,fNone]], columns = ['hot_val', 'upvotes','DD','Daily Discussion','Discussion','Gain','Loss','Meme','Mods','News','Technical Analysis','Weekend Discussion','YOLO','fNone'])

            print('Hot Page Location:',hot_val)
            print('Current Upvotes:',upvotes)
            print('Post Flair:',flair)

            pred = log_reg_clf.predict(page_stats_df[selected_features])
            if pred[0] == 0:
                print("This is UNLIKELY to be a popular post.\n")
            elif pred[0] == 1:
                print("This is LIKELY to be a popular post.\n")

        else:
            print("This is a promoted post.\n")


    #Go find the newest post on /r/wallstreetbets
    newpage_req = Request(url='https://old.reddit.com/r/wallstreetbets/new/',headers=header)
    newpage_sourceCode = urlopen(newpage_req).read().decode()
    newpage_urls = re.findall('<li class="first"><a href="(.*?)" data-event-action="comments"', newpage_sourceCode)
    post_times = re.findall('class="live-timestamp">(.*?)</time>', newpage_sourceCode)
    
    #Get the rising page, since we'll need it later as well
    rising_req = Request(url='https://old.reddit.com/r/wallstreetbets/rising/',headers=header)
    rising_sourceCode = urlopen(rising_req).read().decode()
    rising_urls = re.findall('<li class="first"><a href="(.*?)" data-event-action="comments"', rising_sourceCode)

    #Scrape the first 4 hot pages (so the current top 100 posts + stickied posts)
    hot1_req = Request(url='https://old.reddit.com/r/wallstreetbets/',headers=header)
    hot1_sourceCode = urlopen(hot1_req).read().decode()

    hot2_url = re.findall('<span class="next-button"><a href="(.*?)"', hot1_sourceCode)[0]
    hot2_req = Request(url=hot2_url,headers=header)
    hot2_sourceCode = urlopen(hot2_req).read().decode()

    hot3_url = re.findall('<span class="next-button"><a href="(.*?)"', hot2_sourceCode)[0]
    hot3_req = Request(url=hot3_url,headers=header)
    hot3_sourceCode = urlopen(hot3_req).read().decode()

    hot4_url = re.findall('<span class="next-button"><a href="(.*?)"', hot3_sourceCode)[0]
    hot4_req = Request(url=hot4_url,headers=header)
    hot4_sourceCode = urlopen(hot4_req).read().decode()

    hot_urls = re.findall('<li class="first"><a href="(.*?)" data-event-action="comments"',
               hot1_sourceCode+hot2_sourceCode+hot3_sourceCode+hot4_sourceCode)

    for i in range(len(newpage_urls)):
        if ('minutes' in post_times[i]) and (not newpage_urls[i] in checked_urls):
            checked_urls.append(newpage_urls[i])
            new_post_entry(newpage_urls[i])

#This will run indefinitely, running the post checking sequence every check_timer minutes
while True:
    CheckSucceed = False
    while CheckSucceed == False:
        try:
            check_iterator()
            print('Check iteration complete. Will run another in '+str(check_timer)+' minutes.\n')
            CheckSucceed = True
        except:
            print('There was an issue with that check iteration. Will try again in 3 minutes.\n')
            time.sleep(180)
    time.sleep(check_timer*60)
