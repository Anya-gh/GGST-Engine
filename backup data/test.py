import pandas as pd
import numpy as np
import configparser
import struct
import psutil
import math
import os
import csv
import sys
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris
from sklearn.neighbors import KNeighborsClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.dummy import DummyClassifier

def main():
    raw_data = pd.read_csv("SOL_vs_SOL.csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    snapshots = raw_data.to_numpy()
    X = raw_data.iloc[:, :-1].to_numpy()
    y = raw_data.iloc[:, -1].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)

    train_data = [X_train, y_train]
    test_data = [X_test, y_test]

    log_clf = LogisticRegression(random_state=0, max_iter=10000000).fit(X_train, y_train) # logistic regression
    log_calib_clf = CalibratedClassifierCV(base_estimator=log_clf, cv="prefit").fit(X_test, y_test) # calibration via cross validation

    knn_clf = KNeighborsClassifier(n_neighbors=100).fit(X_train, y_train)

    dummy_clf = DummyClassifier(strategy="most_frequent").fit(X_train, y_train)

    classes = log_clf.classes_
    

    for test_size in [10, 25, 100, 250, 500, 750, len(X_test)]:
        knn_error_sum = 0
        log_error_sum = 0
        log_calib_error_sum = 0
        dummy_error_sum = 0
        for sample in X_test[:test_size]: # dont care about y_test, just the probabilities
            current_snapshot = [sample]
            upper_bound = max(int(sample[1]), int(sample[2]))
            lower_bound = min(int(sample[1]), int(sample[2]))
            moves_dict = {}
            total = 0

            for snapshot in snapshots:
                p1_dist = snapshot[1]
                p2_dist = snapshot[2]
                if (((upper_bound - 100) <= p1_dist <= (upper_bound + 100)) and ((lower_bound - 100) <= p2_dist <= (lower_bound + 100))):
                    option = snapshot[-1]
                    count = moves_dict.get(option)
                    if (count):
                        moves_dict.update({option : (count + 1)})
                    else:
                        moves_dict.update({option : 1})
                    total += 1
                elif (((upper_bound - 100) <= p2_dist <= (upper_bound + 100)) and ((lower_bound - 100) <= p1_dist <= (lower_bound + 100))):
                    option = snapshot[-1]
                    count = moves_dict.get(option)
                    if (count):
                        moves_dict.update({option : (count + 1)})
                    else:
                        moves_dict.update({option : 1})
                    total += 1
            
            log_predictions = log_clf.predict_proba(current_snapshot)[0]
            log_calib_predictions = log_calib_clf.predict_proba(current_snapshot)[0]
            knn_predictions = knn_clf.predict_proba(current_snapshot)[0]
            dummy_predictions = dummy_clf.predict_proba(current_snapshot)[0]

            for index, option in enumerate(classes):
                knn_prediction = knn_predictions[index]
                log_prediction = log_predictions[index]
                log_calib_prediction = log_calib_predictions[index]
                dummy_prediction = dummy_predictions[index]
                if (option in moves_dict):
                    real_prob = (moves_dict.get(option) / total)
                    penalty = 3*(math.log(total, 10))
                    knn_error = (abs((knn_prediction - real_prob)**2)*(penalty))/len(moves_dict)
                    knn_error_sum += knn_error
                    log_error = (abs((log_prediction - real_prob)**2)*(penalty))/len(moves_dict)
                    log_error_sum += log_error
                    log_calib_error = (abs((log_calib_prediction - real_prob)**2)*(penalty))/len(moves_dict)
                    log_calib_error_sum += log_calib_error
                    dummy_error = (abs((dummy_prediction - real_prob)**2)*(penalty))/len(moves_dict)
                    dummy_error_sum += dummy_error

        scale = test_size
        print("Test size: " + str(test_size))
        print("KNN error: " + str(knn_error_sum / scale))
        print("Logistic regression error: " + str(log_error_sum / scale))
        print("Logistic regression (calibrated) error: " + str(log_calib_error_sum / scale))
        print("Dummy error: " + str(dummy_error_sum / scale))
        print()





main()