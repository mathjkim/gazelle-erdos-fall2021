# SIG Data Science Challenge

Attempting to predict the potential popularity of a post made to the financial subreddit /r/wallstreetbets. A project for the Fall 2021 Erdős Institute Data Science Boot Camp.

------------------------------------------------------------------------------------------------------------------------

RedditScraper.py is a python script intended to be run in the background for an extended period of time to allow for data collection from the subreddit. In principle it could be easily modified to work with nearly any subreddit, but here it is focused on /r/wallstreetbets. 

The subreddit scraper is designed to check /r/wallstreetbets every 20 minutes to record any new posts and keep tabs on those posts previously recorded in reddit_wallstreetbets.db, a SQL-based database file. This file contains two tables, one called new_posts, which contains the information initially recorded for each post including information about the submitter's Reddit account, and one called post_stats, which records hourly updates on quantitative indicators of the post's popularity.

Each entry in new_posts records the following information:

post_id - An integer identifier for the entry.

active_track - A Yes/No flag for whether the script is still tracking the post's hourly updates. Tracking is stopped for posts older than a day, as well as those that have been deleted or removed.

title - The text title of the post.

comment_url - A link to the comment section of the post.

flair - The flair of the post, a common Reddit feature for categorizing the type of post.

submit_time - A string that records the date and time the post was submitted.

rising_val - An integer that records the post's location on the rising page, a Reddit feature that indicates recent posts that are rising in popularity. 1 is the top of the page, the quickest rising post so to speak, and 25 is the bottom of the page. Posts that are not on the rising page have a value of 99.

hot_val - An integer that records the post's location on the hot page, which essentially acts as the subreddit home page. Scripts check the first 100 posts on the hot page, so a value of 1 means the post is at the top of the subreddit home page, with increasing values pushing it lower and lower. Posts not found within the top 100 posts on the hot page have a value of 999.

username - The user who submitted the post.

post_karma - How much post karma the user has accumulated on Reddit. Essentially a quantifier for how good/often this user posts on Reddit.

comment_karma - How much comment karma the user has accumulated on Reddit. Essentially a quantifier for how good/often this user comments on Reddit.

redditor_for - How many days the user's Reddit account has existed.

upvotes - How many upvotes the post had when the script initially recorded it.

upvote_percent - Of the total upvotes and downvotes cast on the post, what percentage were upvotes when the script initially recorded it.

num_comments - Number of comments on the post when the script initially recorded it.


Each entry in post_stats records the following information:

stat_id - An integer identifier for the entry.

post_id - An integer identifier that helps link this database to new_posts. This is the same number as that found in new_posts.

comment_url - A link to the comment section of the post. This, too, is the same as what is found in new_posts.

hour - An integer recording how many hours old the post is. New posts are recorded as being 0 hours old and put into this database at the same time as they are added to new_posts.

rising_val - An integer that records the post's location on the rising page at the noted hour age. This is the same parameter as described in new_posts above, simply updated over time.

hot_val - An integer that records the post's location on the hot page at the noted hour age. This is the same parameter as described in new_posts above, simply updated over time.

upvotes - How many upvotes the post had at the noted hour age. This is the same parameter as described in new_posts above, simply updated over time.

upvote_percent - Of the total upvotes and downvotes cast on the post, what percentage were upvotes at the noted hour age.

num_comments - Number of comments on the post at the noted hour age.

------------------------------------------------------------------------------------------------------------------------

Finalclassification.ipynb takes df_24 dataframe as input data. df_24 has the initial features: ['post_id', 'active_track', 'title', 'comment_url',
'link_url', 'flair', 'submit_time', 'rising_val', 'hot_val', 'username','post_karma', 'comment_karma', 'redditor_for', 'upvotes',
'upvote_percent', 'num_comments'] and the value of 'upvotes','hot_val'... after 24 hours.

To answer the question which post becomes viral, any post that has more than mean value of upvotes will be considered viral. Since the 
distribution of upvotes is not uniform this division will only have about 15% of posts as viral. The column 'popularity' represents
this information.

We have turned the problem to a binary classification problem. 

The feature flair is a categorical feature and it is one hot coded after splitting the data to train and test samples.

To choose the significant features a combination of visualization and cross validation on all possible features(without categorical features)
is deployed. 

Several machine learning models are tested: K nearest neighbors, support vector machine, Decision Tree, random forest,
logistic regression and adaboost. For each model the best parameters are chosen by cross validation.

The models performing best are: SVC, DecisionTree, LogisticRegression, KNN and voterClassifier

The final cross validation on these models reveals that logistic regression turns best for accuracy and Voter model for ROC.

Finally the best model is tested on the test samples.
