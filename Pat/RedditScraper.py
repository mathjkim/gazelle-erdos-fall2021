import sqlite3
import pandas as pd
import time

from urllib.request import Request,urlopen
import re

header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
          'AppleWebKit/537.11 (KHTML, like Gecko) '
          'Chrome/23.0.1271.64 Safari/537.11',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
          'Accept-Encoding': 'none',
          'Accept-Language': 'en-US,en;q=0.8',
          'Connection': 'keep-alive'}

check_timer = 20 #minutes


# create a connection to the WSB database file
conn = sqlite3.connect("reddit_wallstreetbets.db")

# create our cursor (this allows us to execute SQL code chunks written as python strings)
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='new_posts'")
if len(c.fetchall()) == 0:
    #Using this if statement to make sure this only runs if the table doesn't exist already
    #create a table for new posts
    c.execute("""CREATE TABLE new_posts(
                        post_id int,
                        active_track text,
                        title text,
                        comment_url text,
                        link_url text,
                        flair text,
                        submit_time text,
                        rising_val int,
                        username text,
                        post_karma int,
                        comment_karma int,
                        redditor_for int,
                        upvotes int,
                        upvote_percent int,
                        num_comments int,
                        PRIMARY KEY (post_id)
                    )""")
    # commit this new table to the database
    conn.commit()

c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='post_stats'")
if len(c.fetchall()) == 0:
    #Using this if statement to make sure this only runs if the table doesn't exist already
    #create a table for hourly post statistics
    c.execute("""CREATE TABLE post_stats(
                        stat_id int,
                        post_id int,
                        comment_url text,
                        hour int,
                        rising_val int,
                        upvotes int,
                        upvote_percent int,
                        num_comments int,
                        PRIMARY KEY (stat_id)
                    )""")
    # commit this new table to the database
    conn.commit()


def check_iterator():
    # Scrape the newest posts to see if they need to be added
    newpage_req = Request(url='https://old.reddit.com/r/wallstreetbets/new/',headers=header)
    newpage_sourceCode = urlopen(newpage_req).read().decode()
    newpage_urls = re.findall('<li class="first"><a href="(.*?)" data-event-action="comments"', newpage_sourceCode)
    post_times = re.findall('class="live-timestamp">(.*?)</time>', newpage_sourceCode)

    #Get the rising page, since we'll need it later as well
    rising_req = Request(url='https://old.reddit.com/r/wallstreetbets/rising/',headers=header)
    rising_sourceCode = urlopen(rising_req).read().decode()
    rising_urls = re.findall('<li class="first"><a href="(.*?)" data-event-action="comments"', rising_sourceCode)

    def new_post_entry(url_str):
        req = Request(url=url_str,headers=header)
        sourceCode = urlopen(req).read().decode()
        time.sleep(1)
       
        deleted_post = False
        if ('<em>[removed]</em>' in sourceCode) or ('<span>[deleted]</span>' in sourceCode):
            deleted_post = True
            #No need to keep tracking deleted posts
            c.execute("UPDATE new_posts SET active_track = 'No' where comment_url = '"+url_str+"'")
            conn.commit()

        if (not '<span class="promoted-tag">' in sourceCode) and (not '?promoted=1' in url_str) and deleted_post==False:
            #this skips promoted and deleted posts
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
                rising_val = rising_urls.index(comment_url)+1
            else:
                rising_val = 99
           
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


            val_str = str(post_id)+",'"+active_track+"','"+title+"','"+comment_url+"','"
            val_str+= link_url+"','"+flair+"','"+submit_time+"',"+str(rising_val)+",'"+username+"',"
            val_str+= str(post_karma).replace(",","")+","+str(comment_karma).replace(",","")+","+str(redditor_for)+","
            val_str+= str(upvotes)+","+str(upvote_percent)+","+str(num_comments)
            #print(val_str)
            c.execute("INSERT INTO new_posts VALUES ("+val_str+")")
            conn.commit()
           
            hours_old = 0
            val_str = str(stat_id)+","+str(post_id)+",'"+url_str+"',"+str(hours_old)+","
            val_str+= str(rising_val)+","+str(upvotes)+","+str(upvote_percent)+","+str(num_comments)
            #print(val_str)
            c.execute("INSERT INTO post_stats VALUES ("+val_str+")")
            conn.commit()


    def old_post_monitor(url_str):
        c.execute("SELECT post_id FROM new_posts WHERE comment_url='"+url_str+"'")
        post_id = list(c.fetchall())[0][0]
        req = Request(url=url_str,headers=header)
        sourceCode = urlopen(req).read().decode()
        time.sleep(1)
       
        deleted_post = False
        if ('<em>[removed]</em>' in sourceCode) or ('<span>[deleted]</span>' in sourceCode):
            deleted_post = True
            #No need to keep tracking deleted posts
            print("Stopping updates for "+url_str+" since it's been deleted/removeed.")
            c.execute("UPDATE new_posts SET active_track = 'No' where comment_url = '"+url_str+"'")
            conn.commit()

        if (not '<span class="promoted-tag">' in sourceCode) and (not '?promoted=1' in url_str) and deleted_post==False:
            #this skips promoted and deleted posts
            upvotes = re.findall('<div class="score"><span class="number">(.*?)</span>', sourceCode)[0]
            upvote_percent = re.findall('span>&#32;\((.*?)% upvoted', sourceCode)[0]
            if url_str in rising_urls:
                rising_val = rising_urls.index(url_str)+1
            else:
                rising_val = 99
            if '<span class="title">no comments (yet)</span>' in sourceCode:
                num_comments = 0
            else:
                num_comments = re.findall('class="bylink comments may-blank" rel="nofollow" >(.*?) comment', sourceCode)[0]
            post_age = re.findall('class="live-timestamp">(.*?)</time>', sourceCode)[0]
            if 'minutes' in post_age:
                hours_old = 0
            elif 'day' in post_age:
                hours_old = 24
                #for simplicity we'll stop tracking posts after they've been up a full day
                c.execute("UPDATE new_posts SET active_track = 'No' where comment_url = '"+url_str+"'")
                conn.commit()
            elif 'hour ago' in post_age:
                hours_old = 1
            else:
                hours_old = int(post_age.replace(' hours ago',''))
           

           
            c.execute("SELECT * FROM post_stats WHERE (comment_url='"+url_str+"' and hour="+str(hours_old)+")")
            if len(c.fetchall()) == 0: #Only add a new entry if that hour hasn't yet been recorded for the post in question
                print('Updating post data in db for '+url_str)
                val_str = str(stat_id)+","+str(post_id)+",'"+url_str+"',"+str(hours_old)+","
                val_str+= str(rising_val)+","+str(upvotes)+","+str(upvote_percent)+","+str(num_comments)
                #print(val_str)
                c.execute("INSERT INTO post_stats VALUES ("+val_str+")")
                conn.commit()

    # Pull database info into a pair of lists
    c.execute("SELECT comment_url FROM new_posts")
    db_comment_urls = list( pd.DataFrame(c.fetchall(), columns = [x[0] for x in c.description])["comment_url"] )
    c.execute("SELECT active_track FROM new_posts")
    db_active_tracks = list( pd.DataFrame(c.fetchall(), columns = [x[0] for x in c.description])["active_track"] )

    # Check posts previously in the database
    print('Checking if posts already in db need to be updated.')
    for i in range(len(db_comment_urls)):
        if db_active_tracks[i] == "Yes":
            #print('Updating post data in db for '+db_comment_urls[i])
            c.execute("SELECT * FROM post_stats")
            stat_id = len(c.fetchall())
            old_post_monitor(db_comment_urls[i])

    # Check posts submitted in the last hour
    print('Checking if new posts need to be added to db.')
    for i in range(len(post_times)):
        if 'minutes' in post_times[i]:
            if not newpage_urls[i] in db_comment_urls:
                c.execute("SELECT * FROM new_posts")
                post_id = len(c.fetchall())
                c.execute("SELECT * FROM post_stats")
                stat_id = len(c.fetchall())
                print('Adding '+newpage_urls[i]+' to db.')
                new_post_entry(newpage_urls[i])

    #Print out database numbers before ending iteration
    c.execute("SELECT * FROM new_posts")
    print( 'new_posts now has '+str(len(pd.DataFrame(c.fetchall(), columns = [x[0] for x in c.description])))+' entries.' )
    c.execute("SELECT * FROM post_stats")
    print( 'post_stats now has '+str(len(pd.DataFrame(c.fetchall(), columns = [x[0] for x in c.description])))+' entries.' )





while True:
    try:
        check_iterator()
        print('Check iteration complete. Will run another in '+str(check_timer)+' minutes.')
    except:
        print('There was an issue with that check iteration. Will try again in '+str(check_timer)+' minutes.')
    time.sleep(check_timer*60)



