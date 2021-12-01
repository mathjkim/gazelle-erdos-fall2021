The Finalclassification takes df_24 dataframe as input data. df_24 has the initial features: ['post_id', 'active_track', 'title', 'comment_url',
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


