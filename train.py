import pandas as pd
import configparser
import struct
import psutil
import math
import os
import csv
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris
from sklearn.neighbors import KNeighborsClassifier as knn
import sys

# in reality you would need 2 char ids, one for player and one for opponent
# but rn we're assuming both the player/opp's character are the same

def main(): # give character id (take as command line arg)
    print(sys.argv[1:][0])
    raw_data = pd.read_csv(sys.argv[1:][0] + ".csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    X = raw_data.iloc[:, :-1]
    y = raw_data.iloc[:, -1]
    #print(X)
    #print(y)
    # classifier = LogisticRegression(random_state=0).fit(X, y)
    # print("predict")
    # print(classifier.predict(X[:2, :]))
    classifier = knn(n_neighbors=3)
    classifier.fit(X, y)
    print(classifier(predict([0,mid,neutral,n/a,n/a])))

    return 0
# def main():
#     X, y = load_iris(return_X_y=True)
#     print("X: ")
#     print(X)
#     print("y: ")
#     print(y)
#     clf = LogisticRegression(random_state=0, max_iter=1000).fit(X, y)
#     print("predict")
#     print(clf.predict(X[:2, :]))
#     print("X[:2, :]")
#     print(X[:2, :])

main()