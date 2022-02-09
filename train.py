import pandas as pd
import numpy as np
import configparser
import struct
import psutil
import math
import os
import csv
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris
from sklearn.neighbors import KNeighborsClassifier as knn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split

import sys

def main(): # give character id of p1 and p2 (take as command line arg)
    codes = ["SOL", "KY", "MAY", "AXL", "CHIPP", "POT", "FAUST", "MILLIA", "ZATO", "RAM", "LEO", "NAGO", 
    "GIO", "ANJI", "INO", "GOLD", "JACKO", "CHAOS"]
    raw_data = pd.read_csv(codes[int(sys.argv[1:][0])] + "_vs_" + codes[int(sys.argv[1:][1])] + ".csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    
    #raw_data = pd.read_csv(sys.argv[1:][0] + "_vs_" + sys.argv[1:][1] + ".csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    X = raw_data.iloc[:, :-1].to_numpy()
    y = raw_data.iloc[:, -1].to_numpy()
    #print(X)
    #print(y)
    X_train, X_calib, y_train, y_calib = train_test_split(X, y, random_state=42)

    base_clf = LogisticRegression(random_state=0, max_iter=100000).fit(X_train, y_train)
    calibrated_clf = CalibratedClassifierCV(base_estimator=base_clf, cv="prefit").fit(X_calib, y_calib)

    classes = base_clf.classes_

    sample = (X[:1,:])
    print(sample)
    print("---")

    base_predictions = base_clf.predict_proba(sample)[0]
    calibrated_predictions = calibrated_clf.predict_proba(sample)[0]
    for index, option in enumerate(classes):
        print(option)
        print("base: " + str(base_predictions[index]))
        print("calibrated: " + str(calibrated_predictions[index]))
        print()

def evaluateSnapshot(snapshot, p1_char, p2_char, opp_classifier, mode): # mode <- {1, 2}, 1 is offense, 2 is defense. classifier is assumed to be correct mode, just used for gatlings.

        # snapshot should be from opponent's perspective
        # i.e. opponentData should be playerData in the snapshot

        # does not take into account frame advantage.
        # does not take into account gatlings (which bypass frame advantage, and should have startup of 0)

        config_player = configparser.ConfigParser()
        config_player.read(str(p1_char) + '.ini')
        config_opponent = configparser.ConfigParser()
        config_opponent.read(str(p2_char) + '.ini')
        frame_adv = int(snapshot[0][0])

        player_options = config_player['options']['list'].split(',')
        opponent_options = config_opponent['options']['list'].split(',')
        player_moves = config_player['moves']['option_names'].split(',')
        opponent_moves = config_opponent['moves']['option_names'].split(',')

        probabilities = (opp_classifier.predict_proba(snapshot)[0]).tolist()
        #print(probabilities)
        classes = (opp_classifier.classes_).tolist()
        gatlings = snapshot[0][5:] # some kind of interpretation
        gatling_options = []
        corrected_options = []
        corrected_probabilities = []
        nothing_probability = 0
        for option in classes:
            probability = probabilities[classes.index(option)]
            if (probability > 0.05):
                corrected_options.append(option)
                corrected_probabilities.append(probability)
            else:
                nothing_probability += probability
        
        for index, gatling in enumerate(gatlings):
            gatling = int(gatling)
            if (gatling == 1):
                if (mode == 1): # gatlings are for player
                    gatling_options.append(player_moves[index])
                elif (mode == 2): # gatlings are for opponent
                        gatling_options.append(opponent_moves[index])
        
        print(gatling_options)

        snapshot = snapshot[0].tolist()

        option_evals = []

        dist_diff = abs(snapshot[1] - snapshot[2])

                # clearly, this is not perfect.
                # doesn't take into account invuln on some moves;
                # doesn't take into account counter hit advantage being bigger on some moves;
                # doesn't take into account recovery frames if both moves are out of range (potentially moves out of range should just be ignored, with exception for moves like 2S and 6P);
                # doesn't take into account backdash, block etc. as options
                # inexhaustive, will add to list once more things come to mind.

        for player_option in player_options:
            player_option = config_player[player_option]
            player_option_evaluation = 0
            bubble = 0
            player_range = int(player_option['range'], 10)
            player_startup = int(player_option['startup'], 10) + frame_adv
            player_invuln = player_option['invuln']
            player_guard = player_option['guard']

            if (mode == 1): # i.e. player's option is a gatling, therefore bypasses frame_adv
                if (player_option['name'] in gatling_options):
                    player_startup = 0

            player_recovery = int(player_option['recovery'], 10)
            player_adv = int(player_option['adv'], 10)
            for opponent_option in opponent_options:
                opponent_option = config_player[opponent_option]
                if (opponent_option['name'] in corrected_options):
                    winning_option = 0 # 1 if player option wins, -1 if it loses, 0 if nothing happens
                    opponent_option_weight = corrected_probabilities[corrected_options.index(opponent_option['name'])]
                    opponent_range = int(opponent_option['range'], 10)
                    opponent_startup = int(opponent_option['startup'], 10) - frame_adv
                    opponent_invuln = opponent_option['invuln']
                    opponent_guard = opponent_option['guard']

                    if (mode == 2): # i.e. opponent's option is a gatling, therefore bypasses frame_adv
                        if (player_option['name'] in gatling_options):
                            opponent_startup = 0
                    
                    if ((opponent_range < dist_diff) and (player_range >= dist_diff)):
                        winning_option = 1
                        bubble = 1
                    elif ((player_range < dist_diff) and (opponent_range >= dist_diff)):
                        winning_option = -1
                        bubble = 2
                    elif ((player_range < dist_diff) and (opponent_range < dist_diff)):
                        winning_option = 0
                        bubble = 3
                    else:
                        if (player_invuln == "all"):
                            winning_option = 1
                            bubble = 4
                        elif ((player_invuln == "low") and (opponent_guard != "low")):
                            winning_option = 1
                            bubble = 5
                        elif ((player_invuln == "high") and (opponent_guard != "high")):
                            winning_option = 1
                            bubble = 6
                        elif (opponent_invuln == "all"):
                            winning_option = -1
                            bubble = 7
                        elif ((opponent_invuln == "low") and (player_guard != "low")):
                            winning_option = -1
                            bubble = 8
                        elif ((opponent_invuln == "high") and (player_guard != "high")):
                            winning_option = -1
                            bubble = 9
                        else:
                            if (player_startup > opponent_startup):
                                winning_option = -1
                                bubble = 10
                            elif (opponent_startup > player_startup):
                                winning_option = 1
                                bubble = 11
                            else:
                                winning_option = 0
                                bubble = 12
                    if (player_option['name'] == "6P"):
                        print(opponent_option['name'] + ": " + str(winning_option) + ": " + str(bubble))
                    option_eval = opponent_option_weight * winning_option
                    player_option_evaluation += opponent_option_weight * winning_option
            wins_nothing = 0
            wins_backdash = 0
            wins_run = 0 # will need to think about this one
            whiff_punishable = 0
            if ((player_startup + player_recovery) > 16 + 10): # +10 is for fastest option
                whiff_punishable = 1
            if (player_range < dist_diff): # move will whiff if opponent does nothing
                if (whiff_punishable): # move is whiff punishable
                    wins_nothing = -1
            else: # move will get blocked
                if (player_adv > 0):
                    wins_nothing = player_adv / 10
                elif (player_adv > -10): # not block punishable
                    wins_nothing = -0.5
                else:
                    wins_nothing = -(2 ** abs(player_adv / 30))
                if (player_range < dist_diff + 800): # backdash range assumed to be 800 for all chars
                    if (whiff_punishable):
                        wins_backdash = -1
                    else:
                        wins_backdash = 0.5 # slight advantage since they push themselves away/toward corner
            player_option_evaluation += wins_backdash * probabilities[classes.index("backdash")]
            player_option_evaluation += wins_nothing * nothing_probability
                    

            option_evals.append(player_option['name'] + ": " + str(player_option_evaluation))
        
        return option_evals

main()