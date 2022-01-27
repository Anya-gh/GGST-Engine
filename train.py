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
import sys

# in reality you would need 2 char ids, one for player and one for opponent
# but rn we're assuming both the player/opp's character are the same

def main(): # give character id of p1 and p2 (take as command line arg)
    characters = ["SOL", "KY", "MAY", "AXL", "CHIPP", "POT", "FAUST", "MILLIA", "ZATO", "RAM", "LEO", "NAGO", 
    "GIO", "ANJI", "INO", "GLDS", "JACKO", "CHAOS"]
    #raw_data = pd.read_csv(characters[sys.argv[1:][0]] + "_vs_" + characters[sys.argv[1:][1]] + ".csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    raw_data = pd.read_csv(csys.argv[1:][0] + "_vs_" + sys.argv[1:][1] + ".csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    X = raw_data.iloc[:, :-1].to_numpy()
    y = raw_data.iloc[:, -1].to_numpy()
    #print(X)
    #print(y)
    classifier = LogisticRegression(random_state=0, max_iter=100000).fit(X, y)
    print("prediction")
    sample = (X[:1,:])
    print(sample)
    #print(sample)
    #print(classifier.predict_proba(sample))
    #print(classifier.predict(sample))
    #print(classifier.classes_)
    evaluation = evaluateSnapshot(sample, 0, 0, classifier)
    print(evaluation)
    print()
    # sample_2 = np.array([[-4,1816.270263671875,3322.479736328125,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]])
    # print(sample_2)
    # eval_2 = evaluateSnapshot(sample_2, 0, 0, classifier)
    # print(eval_2)
    # print()
    sample_3 = np.array([[3,2032.295654296875,1482.1551513671875,0,0,0,0,0,1,1,1,1,1,1,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0]])
    print(sample_3)
    probabilities = (classifier.predict_proba(sample_3)[0]).tolist()
    classes = (classifier.classes_).tolist()
    for option in classes:
        print(option + ": " + str(probabilities[classes.index(option)]))
    eval_3 = evaluateSnapshot(sample_3, 0, 0, classifier)
    print(eval_3)
    #classifier = knn(n_neighbors=3)
    #classifier.fit(X, y)

def evaluateSnapshot(snapshot, p1_char, p2_char, opp_classifier, gatling): # gatling <- {0, 1, 2}, denotes which character has the gatlings. 0 is ignore

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

        probabilities = (opp_classifier.predict_proba(snapshot)[0]).tolist()
        #print(probabilities)
        classes = (opp_classifier.classes_).tolist()
        gatlings = snapshot[0][5:] # some kind of interpretation
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
        
        # for option in classes:
        #     print(option)
        #     print(probabilities[classes.index(option)])

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
            player_recovery = int(player_option['recovery'], 10)
            player_adv = int(player_option['adv'], 10)
            for opponent_option in opponent_options:
                opponent_option = config_player[opponent_option]
                if (opponent_option['name'] in corrected_options):
                    winning_option = 0 # 1 if player option wins, -1 if it loses, 0 if nothing happens
                    opponent_option_weight = corrected_probabilities[corrected_options.index(opponent_option['name'])]
                    opponent_range = int(opponent_option['range'], 10)
                    opponent_startup = int(opponent_option['startup'], 10) - frame_adv  
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
                        if (player_startup > opponent_startup):
                            winning_option = -1
                            bubble = 4
                        elif (opponent_startup > player_startup):
                            winning_option = 1
                            bubble = 5
                        else:
                            winning_option = 0
                            bubble = 6 
                    
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