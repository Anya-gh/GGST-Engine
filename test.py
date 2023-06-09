import pandas as pd
import numpy as np
import configparser
import struct
import psutil
import math
import os
import csv
import sys
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris
from sklearn.neighbors import KNeighborsClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.ensemble import AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.feature_selection import SelectPercentile, f_classif, mutual_info_classif, VarianceThreshold
from sklearn import preprocessing

def main(): # give character id of p1 and p2 (take as command line arg)
    codes = ["SOL", "KY", "MAY", "AXL", "CHIPP", "POT", "FAUST", "MILLIA", "ZATO", "RAM", "LEO", "NAGO", 
    "GIO", "ANJI", "INO", "GOLD", "JACKO", "CHAOS"]
    raw_data = pd.read_csv("SOL_vs_SOL.csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    snapshots = raw_data.to_numpy()
    X = raw_data.iloc[:, :-1].to_numpy()
    y = raw_data.iloc[:, -1].to_numpy()

    # minmax_scaler = preprocessing.MinMaxScaler()
    # maxabs_scaler = preprocessing.MaxAbsScaler()
    # robust_scaler = preprocessing.RobustScaler()
    # X_train = minmax_scaler.fit_transform(X)

    # test_data = [
    # [1.0,1.0,0.0010000000474974513,0.0,1.0,1.0,0.0,0.0,653.43603515625,-653.477783203125,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], #1
    # [1.0,0.7879999876022339,0.19779999554157257,0.06650000065565109,1.0,1.0,0.0,0.15625,-1113.123046875,-1629.288330078125,2,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0], #5
    # [0.3499999940395355,0.4332999885082245,0.7364000082015991,0.12999999523162842,0.43666666746139526,1.0,0.0,0.3189062476158142,-637.239013671875,535.676025390625,-7,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0] #161
    # ]

    columns = ["player hp", "opponent hp", "player tension", "opponent tension", "player burst", "opponent burst", "player risc", "opponent risc", "player dist", "opponent dist", "frame adv", "player wakeup", "opponent wakeup"]
    
    for x in ["(player) 5P","(player) 5K","(player) c.S","(player) f.S","(player) 5H","(player) 5D","(player) 6P","(player) 6S","(player) 6H","(player) 2P","(player) 2K","(player) 2S","(player) 2H","(player) 2D"]:
        columns.append(str(x))

    for x in ["(opponent) 5P","(opponent) 5K","(opponent) c.S","(opponent) f.S","(opponent) 5H","(opponent) 5D","(opponent) 6P","(opponent) 6S","(opponent) 6H","(opponent) 2P","(opponent) 2K","(opponent) 2S","(opponent) 2H","(opponent) 2D"]:
        columns.append(str(x))


    X_labelled = pd.DataFrame(X, columns=columns)

    fc_selector = SelectPercentile(f_classif, percentile=50)
    X_train_fc = fc_selector.fit_transform(X, y)
    fc_labels = X_labelled.columns[fc_selector.get_support()]
    print(fc_labels)
    mic_selector = SelectPercentile(mutual_info_classif, percentile=25)
    X_train_mic = mic_selector.fit_transform(X, y)
    mic_labels = X_labelled.columns[mic_selector.get_support()]
    print(mic_labels)
    var_selector = VarianceThreshold(threshold=(0.1))
    X_train_var = var_selector.fit_transform(X, y)
    var_labels = X_labelled.columns[var_selector.get_support()]
    print(var_labels)
    # test_data = [X[0]]
    # test_data.append(X[4])
    # test_data.append(X[160])

    # X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42)
    # X_train = np.delete(X, [0, 4, 160], 0)
    # y_train = np.delete(y, [0, 4, 160], 0)

    # plt.subplot(111)
    # plt.bar(columns, var_scores)
    # plt.ylim(ymin=0, ymax=50)
    
    # plt.xticks(rotation=90)
    # plt.show()
    test_data_unscaled = [np.copy(X[0])]
    test_data_unscaled.append(np.copy(X[4]))
    test_data_unscaled.append(np.copy(X[160]))

    X_train = np.copy(X)
    #print(X[0])
    for index, train_sample in enumerate(X_train):
        train_sample[8] = (train_sample[8] / 1700)
        train_sample[9] = (train_sample[9] / 1700)
        train_sample[10] = (train_sample[10] / 15)
        X_train[index] = train_sample
    test_data_scaled = [X_train[0]]
    test_data_scaled.append(X_train[4])
    test_data_scaled.append(X_train[160])
    X_train = np.delete(X_train, [0, 4, 160], 0)

    for index, train_sample in enumerate(X_train_var):
        train_sample[0] = (train_sample[0] / 1700)
        train_sample[1] = (train_sample[1] / 1700)
        train_sample[2] = (train_sample[2] / 15)
        X_train_var[index] = train_sample
    test_data_var = [X_train_var[0]]
    test_data_var.append(X_train_var[4])
    test_data_var.append(X_train_var[160])
    X_train_var = np.delete(X_train_var, [0, 4, 160], 0)

    for index, train_sample in enumerate(X_train_mic):
        train_sample[6] = (train_sample[6] / 1700)
        train_sample[7] = (train_sample[7] / 1700)
        train_sample[8] = (train_sample[8] / 15)
        X_train_mic[index] = train_sample
    test_data_mic = [X_train_mic[0]]
    test_data_mic.append(X_train_mic[4])
    test_data_mic.append(X_train_mic[160])
    X_train_mic = np.delete(X_train_mic, [0, 4, 160], 0)
    X_unscaled = np.delete(X, [0, 4, 160], 0)
    y_train = np.delete(y, [0, 4, 160], 0)

    train_data = [["unscaled", X_unscaled], ["scaled", X_train], ["mic", X_train_mic], ["var", X_train_var]]
    test_data = [test_data_unscaled, test_data_scaled, test_data_mic, test_data_var]
    
    classifiers = []

    base_clf = LogisticRegression(random_state=0, max_iter=10000000)
    classes = base_clf.fit(X_unscaled, y_train).classes_
    classifiers.append(["log reg", base_clf])

    #calibrated_clf = CalibratedClassifierCV(base_estimator=base_clf, cv="prefit").fit(X_calib, y_calib)

    knn_clf = KNeighborsClassifier(n_neighbors=100)
    classifiers.append(["knn", knn_clf])

    ada_clf = AdaBoostClassifier(base_estimator = base_clf, n_estimators=10, random_state=0)
    classifiers.append(["ada", ada_clf])
    
    nb_clf = GaussianNB()
    classifiers.append(["nb", nb_clf])

    labels = ["throw","5P","5K","c.S","f.S","5H","5D","6P","6S","6H","2P","2K","2S","2H","2D","DP","wild throw","fafnir","burst"]

    results = []
    
    for classifier in classifiers:
        name = classifier[0]
        classifier_results = []
        for index, train_set in enumerate(train_data):
            data = train_set[1]
            data_name = train_set[0]
            clf = classifier[1].fit(data, y_train)
            print(name + ": " + data_name)
            for i, coef in enumerate(clf.coef_):
                print(classes[i])
                for x, c in enumerate(coef):
                    print(columns[x] + ": " + str(c))
            print()
            snapshot_predictions = []
            for sample in test_data[index]:
                snapshot = [sample]
                snapshot_predictions.append(clf.predict_proba(snapshot)[0])
            classifier_results.append([data_name, snapshot_predictions])
        results.append([name, classifier_results]) #0 log reg, #1 knn, #2 ada, #3 nb

    # log_results = results[0]
    # knn_results = results[1]
    # ada_results = results[2]
    # nb_results = results[3]

    # x_label_loc = np.arange(len(classes))  # the label locations
    # width = 0.2  # the width of the bars

    # fig, ax = plt.subplots()
    # for index, train_set in enumerate(train_data):
    #     rects = ax.bar(x_label_loc + (width * (index - 2)), ada_results[1][index][1][0], width, label=ada_results[1][index][0]) # sample is last
    #     #ax.bar_label(rects)
    # ax.set_xticks(x_label_loc, classes)
    # ax.set_ylabel('Probability')
    # ax.set_xlabel('Options')
    # ax.legend()
    # fig.tight_layout()

    # plt.show()

    # sizes = [100, 200, 300, 400, 500, 600, 700, 800, 907]

    # convergence_results = []
    # #for classifier in classifiers:    
    # classifier = classifiers[0]
    # name = classifier[0]
    # classifier_results = []
    # for index, train_set in enumerate(train_data):
    #     set_results = []
    #     data_name = train_set[0]
    #     prev_predictions = []
    #     for size in [100, 200, 300, 400, 500, 600, 700, 800, len(train_set[1])]:
    #         print(size)
    #         data = train_set[1][:size]
    #         clf = classifier[1].fit(data, y_train[:size])
    #         convergence_sum = 0
    #         current_predictions = []
    #         clf_classes = clf.classes_
    #         print(clf_classes)
    #         for s_index, sample in enumerate(test_data[index]):
    #             print(s_index)
    #             # print("len: " + str(len(prev_predictions))) # 2 because there are two lists that make this list
    #             sample_results = []
    #             snapshot = [sample]
    #             predictions = clf.predict_proba(snapshot)[0]
    #             prev_index = 0
    #             for p_index, prediction in enumerate(predictions):
    #                 if (len(prev_predictions) == 0):
    #                     difference = 0
    #                 elif (clf_classes[p_index] != prev_predictions[0][prev_index]):
    #                     difference = 0
    #                 else:
    #                     difference = abs(prediction - prev_predictions[1][s_index][prev_index])
    #                     convergence_sum += (difference)
    #                     prev_index += 1
    #             convergence_sum /= len(predictions)
    #             current_predictions.append(predictions)
    #         prev_predictions = [clf_classes, current_predictions]
    #         convergence_sum /= 3

    #         #convergence_sum /= len(test_data[index])
    #         set_results.append(convergence_sum)
    #     classifier_results.append([data_name, set_results])
    # #convergence_results.append([name, classifier_results])

    # print(classifier_results)

    # fig, ax = plt.subplots()
    # for index, train_set in enumerate(train_data):
    #     lines = ax.plot(sizes, classifier_results[index][1], label=classifier_results[index][0])
    # ax.set_ylabel('Difference')
    # ax.set_xlabel('Test size')
    # ax.legend()
    # plt.show()
            

main()