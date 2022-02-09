import ctypes as c
from tkinter import *
from tkinter import ttk
from ctypes import wintypes as w
from subprocess import check_output
import ModuleEnumerator
import configparser
import struct
import psutil
import math
import os
import csv
import sys
import time
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split

characters = ["Sol Badguy", "Ky Kiske", "May", "Axl Low", "Chipp Zanuff", "Potemkin", "Faust", "Millia Rage", "Zato-1", "Ramlethal Valentine", "Leo Whitefang", "Nagoriyuki", 
    "Giovanna", "Anji Mito", "I-No", "Goldlewis Dickinson", "Jack-O", "Happy Chaos"]

codes = ["SOL", "KY", "MAY", "AXL", "CHIPP", "POT", "FAUST", "MILLIA", "ZATO", "RAM", "LEO", "NAGO", 
    "GIO", "ANJI", "INO", "GLDS", "JACKO", "CHAOS"]

sol_moves = ["5P","5K","5H","c.S","f.S","5D","6P","6H","6S","2P","2K","2H","2S","2D"]

confirm_pressed = False

k32 = c.windll.kernel32

OpenProcess = k32.OpenProcess
OpenProcess.argtypes = [w.DWORD,w.BOOL,w.DWORD]
OpenProcess.restype = w.HANDLE

ReadProcessMemory = k32.ReadProcessMemory
ReadProcessMemory.argtypes = [w.HANDLE,w.LPCVOID,w.LPVOID,c.c_size_t,c.POINTER(c.c_size_t)]
ReadProcessMemory.restype = w.BOOL

GetLastError = k32.GetLastError
GetLastError.argtypes = None
GetLastError.restype = w.DWORD

CloseHandle = k32.CloseHandle
CloseHandle.argtypes = [w.HANDLE]
CloseHandle.restype = w.BOOL

def getPID():
    PROCNAME = "GGST-Win64-Shipping.exe"

    for proc in psutil.process_iter():
        if proc.name() == PROCNAME:
            return proc.pid
    
    return -1

def GetValueFromAddress(processHandle, address, isFloat=False, is64bit=False, isString=False):
    if isString:
        data = c.create_string_buffer(16)
        bytesRead = c.c_ulonglong(16)
    elif is64bit:
        data = c.c_ulonglong()
        bytesRead = c.c_ulonglong()
    else:
        data = c.c_ulong()
        bytesRead = c.c_ulonglong(4)

    successful = ReadProcessMemory(processHandle, address, c.byref(data), c.sizeof(data), c.byref(bytesRead))
    if not successful:
        e = GetLastError()
        print("ReadProcessMemory Error: Code " + str(e))

    value = data.value

    if isFloat:
        value = data
        return struct.unpack("<f", value)[0]
    elif isString:
        try:
            return value.decode('utf-8')
        except:
            print("ERROR: Couldn't decode string from memory")
            return "ERROR"
    else:
        return int(value)

def GetValueFromPointer(processHandle, base, section):
    data = c.c_ulonglong()
    bytesRead = c.c_ulonglong()
    config = configparser.ConfigParser()
    config.read('addresses.ini')
    address = int(config[section]['base_offset'], 0) + base
    successful = ReadProcessMemory(processHandle, address, c.byref(data), c.sizeof(data), c.byref(bytesRead))
    for key in config[section]:
        if (key != 'base_offset'):
            successful = ReadProcessMemory(processHandle, address, c.byref(data), c.sizeof(data), c.byref(bytesRead))
            address = int(data.value) + int(config[section][key], 0)
            if not successful:
                e = GetLastError()
                print("ReadProcessMemory Error: Code " + str(e))
    final = c.c_short()
    successful = ReadProcessMemory(processHandle, address, c.byref(final), c.sizeof(final), c.byref(bytesRead))
    return final.value

def check_pid(pid):        
    """ Check For the existence of a unix pid. """
    return psutil.pid_exists(pid)

class PlayerData:
    
    def __init__(self, player_id, hp_offset, lives_offset, tension_offset, burst_offset, dist_offset, char_offset):
        self.player_id = player_id
        self.hp_offset = int(hp_offset, 0)
        self.lives_offset = int(lives_offset, 0)
        self.tension_offset = int(tension_offset, 0)
        self.burst_offset = int(burst_offset, 0)
        self.dist_offset = int(dist_offset, 0)
        self.char_offset = int(char_offset, 0)
        self.hp = -1
        self.lives_lost = -1
        self.lives_changed = 0
        self.tension = -1
        self.tension_record = self.tension
        self.burst = -1
        self.dist = -1
        self.char = -1
        self.action = -99
        self.prev_action = -99
        self.actionChange = -1
    
    def updateData(self, processHandle, base, pid):
        if(check_pid(pid)):
            self.hp = GetValueFromAddress(processHandle, base + self.hp_offset, isFloat=True)
            lives = self.lives_lost
            self.lives_lost = GetValueFromAddress(processHandle, base + self.lives_offset)
            if (self.lives_lost > lives):
                self.lives_changed = 1
            self.tension = GetValueFromAddress(processHandle, base + self.tension_offset, isFloat=True)
            self.burst = GetValueFromAddress(processHandle, base + self.burst_offset, isFloat=True)
            self.dist = GetValueFromAddress(processHandle, base + self.dist_offset, isFloat=True)
            self.char = GetValueFromAddress(processHandle, base + self.char_offset)
            temp = self.action
            self.action = GetValueFromPointer(processHandle, base, str(self.char) + '_p' + str(self.player_id))
            config = configparser.ConfigParser()
            config.read(str(self.char) + '.ini')

            try:
                if (config[str(abs(self.action))]['name'] != config[str(abs(temp))]['name']):
                    self.tension_record = self.tension
                    self.prev_action = temp
                    self.actionChange = 1
                # elif (self.tension != self.tension_record): # for checking if the same move was done twice in a row
                #     self.tension_record = self.tension
                #     self.prev_action = temp
                #     self.actionChange = 1
            except KeyError:
                k = 0
        else:
            print("PID not found. The game probably isn't running.")

class GameState:

    def __init__(self, classifier_1, classifier_2, player_side):
        self.p1_frame_adv = 0
        self.p2_frame_adv = 0
        self.dist_diff = 0
        # need to know dist from corner, dont currently know this info yet. will require scanning.
        self.p1_last_move = -99
        self.p2_last_move = -99
        self.p1_blocked = 0 # for p2
        self.p1_wakeup = 0
        self.p1_blocking = 0 # for p1 
        self.p2_blocked = 0 # for p1
        self.p2_wakeup = 0
        self.p2_blocking = 0 # for p2
        self.p1_frame_counter = 0
        self.p2_frame_counter = 0
        self.classifier_1 = classifier_1
        self.classifier_2 = classifier_2
        self.output = None
        self.player_side = player_side
        #self.state = "" # ground, air, wake-up, hit-stun (Idk some more as well maybe)
        # ignore for now

    def createSnapshot(self, p1_data, p2_data, player, action): # for whomst is the snapshot
        playerData = None
        opponentData = None
        player_last_move = -99
        opponent_last_move = -99
        player_blocked = -1
        opponent_blocked = -1
        player_wakeup = -1
        opponent_wakeup = -1
        frame_adv = 0

        if (player == 1):
            playerData = p1_data
            opponentData = p2_data
            player_last_move = self.p1_last_move
            opponent_last_move = self.p2_last_move
            player_blocked = self.p1_blocking
            opponent_blocked = self.p2_blocked
            player_wakeup = self.p1_wakeup
            opponent_wakeup = self.p2_wakeup
            frame_adv = self.p1_frame_adv
        elif (player == 2):
            playerData = p2_data
            opponentData = p1_data
            player_last_move = self.p2_last_move
            opponent_last_move = self.p1_last_move
            player_blocked = self.p2_blocking
            opponent_blocked = self.p1_blocked
            player_wakeup = self.p2_wakeup
            opponent_wakeup = self.p1_wakeup
            frame_adv = self.p2_frame_adv
    
        config_player = configparser.ConfigParser()
        config_player.read(str(playerData.char) + '.ini')
        config_opponent = configparser.ConfigParser()
        config_opponent.read(str(opponentData.char) + '.ini')
            
        player_last = config_player[str(abs(player_last_move))]
        opponent_last = config_player[str(abs(opponent_last_move))]

        player_gatlings = []
        opponent_gatlings = []
        player_moves = config_player['moves']['list'].split(',')
        opponent_moves = config_opponent['moves']['list'].split(',')

        # if ((player_blocked == 0) or (opponent_last['name'] == "shimmy")):
        #     opponent_last = "n/a"
        # if ((opponent_blocked == 0) or (player_last['name'] == "shimmy")):
        #     player_last = "n/a"
        if (opponent_blocked == 1):
            player_gatlings = player_last['gatling'].split(',')
        elif (player_blocked == 1):
            opponent_gatlings = opponent_last['gatling'].split(',')

        index_list = []
        output = []
        output.append(frame_adv)
        output.append(playerData.dist)
        output.append(opponentData.dist)

        # output.append(player_blocked)
        # output.append(opponent_blocked)

        # nvm, some options dont have gatlings so throwing this in after all
        # ofc could still use frame_adv greater/less than 0 but probably better this way
        # nvm the nvm. if frame_adv is 0, why do you care that they blocked the attack even if they did

        # dont think these are actually necessary, its obvious who blocked because the player/opps gatlings are separate
        # could use to reduce size of entries in data set since in sol vs sol gatlings are same
        
        # knowing who's gatlings they are is important for eval function. so, they need to go back in.
        # but this could just be passed straight to the evaluation function. In fact, since p1 and p2's gatlings are
        # separate, you can figure out who's gatlings they are. this might be hard to do with past data but is very easy
        # to do with live data.

        output.append(player_wakeup) # this is wakeup
        output.append(opponent_wakeup) # this is oki
        #output.append(self.opponent_wakeup)
        if (player_blocked == 0):
            for move in player_moves:
                if move in player_gatlings:
                    output.append(1)
                else:
                    output.append(0)
        else:
            for move in opponent_moves:
                if move in opponent_gatlings:
                    output.append(1)
                else:
                    output.append(0)
        output.append(action['name'])
        return output

    def writeSnapshot(self, snapshot, playerData, opponentData, player_blocked):
        if (player_blocked == 0):
            with open(codes[playerData.char] + '_vs_' + codes[opponentData.char] + '.csv', 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(snapshot)
        else:
            with open(codes[opponentData.char] + '_vs_' + codes[playerData.char] + '.csv', 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(snapshot)

    def evaluateSnapshot(self, snapshot, playerChar, opponentChar, opp_classifier, mode): # mode <- {0, 1}, 0 is offense, 1 is defense. classifier is assumed to be correct mode, just used for gatlings.

        # snapshot should be from opponent's perspective
        # i.e. opponentData should be playerData in the snapshot
        action = snapshot[-1]
        snapshot = snapshot[:-1]
        snapshot = np.array([snapshot])

        config_player = configparser.ConfigParser()
        config_player.read(str(playerChar) + '.ini')
        config_opponent = configparser.ConfigParser()
        config_opponent.read(str(opponentChar) + '.ini')

        frame_adv = int(snapshot[0][0])

        player_options = config_player['options']['list'].split(',')
        opponent_options = config_opponent['options']['list'].split(',')
        player_moves = config_player['moves']['option_names'].split(',')
        opponent_moves = config_opponent['moves']['option_names'].split(',')

        probabilities = (opp_classifier.predict_proba(snapshot)[0]).tolist()
        #print(probabilities)
        classes = (opp_classifier.classes_).tolist()
        gatlings = snapshot[0][5:-1] # some kind of interpretation
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
        
        snapshot = snapshot[0].tolist()

        option_evals = []

        dist_diff = abs(float(snapshot[1]) - float(snapshot[2]))

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

            if (mode == 0): # i.e. player's option is a gatling, therefore bypasses frame_adv
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

                    if (mode == 1): # i.e. opponent's option is a gatling, therefore bypasses frame_adv
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
                    

            #option_evals.append(player_option['name'] + ": " + str(player_option_evaluation))
            option_evals.append([player_option['name'], player_option_evaluation])
        
        # print("Frame advantage: " + str(frame_adv * -1))
        # print("Player dist: " + str(snapshot[2]))
        # print("Opponent dist: " + str(snapshot[1]))
        # for index, option_eval in enumerate(option_evals):
        #     #if (option_eval > 0):
        #     print(player_moves[index] + ": " + str(option_eval))
        # print("Selected option evaluation: " + str(option_evals[player_moves.index(action)]))

        # label_frame_adv.configure(text = str(frame_adv * -1))
        # label_dist.configure(text = str(dist_diff))
        # label_option.configure(text = ("Selected: " + action + " - " + str(option_evals[player_moves.index(action)])))
        # best_option = player_moves[option_evals.index(max(options_evals))]
        # label_best.configure(text = ("Best: " + best_option + " - " + str(max(options_evals))))

        return option_evals

    def updateData(self, p1_data, p2_data):
        
        config_p1 = configparser.ConfigParser()
        config_p1.read(str(p1_data.char) + '.ini')
        config_p2 = config_p1
        if (p1_data.char != p2_data.char):
            config_p2 = configparser.ConfigParser()
            config_p2.read(str(p2_data.char) + '.ini')

        try:
            p1_action = config_p1[str(abs(p1_data.action))]
            p2_action = config_p2[str(abs(p2_data.action))]

            if (p1_data.actionChange == 1): # player 1 takes an action
                if ((p1_action['name'] != "block") and (p1_action['name'] != "shimmy") and (self.player_side == 1)):
                    snapshot = self.createSnapshot(p1_data, p2_data, 2, p1_action) # snapshot needs to be opponent pov
                    evals = []
                    if (self.p1_blocking == 1):
                        evals = self.evaluateSnapshot(snapshot, p1_data.char, p2_data.char, self.classifier_2, 1)
                    else:
                        evals = self.evaluateSnapshot(snapshot, p1_data.char, p2_data.char, self.classifier_1, 0)
                    self.output = [self.p1_frame_adv, snapshot[1:], evals, p1_action['name']]
                    self.p1_blocking = 0

                self.p1_frame_counter = time.time()
                self.p2_blocked = 0
                self.p1_wakeup = 0
                self.p1_frame_adv = 0
                p1_data.actionChange = 0

            if (p2_data.actionChange == 1):
                if ((p2_action['name'] != "block") and (p2_action['name'] != "shimmy") and (self.player_side == 2)):
                    snapshot = self.createSnapshot(p1_data, p2_data, 1, p2_action) # snapshot needs to be opponent pov
                    evals = []
                    if (self.p2_blocking == 1):
                        evals = self.evaluateSnapshot(snapshot, p2_data.char, p1_data.char, self.classifier_1, 1)
                    else:
                        evals = self.evaluateSnapshot(snapshot, p2_data.char, p1_data.char, self.classifier_2, 0)
                    self.output = [self.p2_frame_adv, snapshot[1:], evals, p2_action['name']]
                    self.p2_blocking = 0
                    
                self.p2_frame_counter = time.time()
                self.p1_blocked = 0
                self.p2_wakeup = 0
                self.p2_frame_adv = 0 # run through example to see why this is necessary (or not?)
                p2_data.actionChange = 0
            
            #p1_active = p1_action['active']
            #print((time.time() - self.p1_frame_counter))
            if (p1_action['startup'] != "n/a"):
                p1_startup = int(p1_action['startup'], 0)
                if (((time.time() - self.p1_frame_counter) * 60) > p1_startup):
                    if (p2_action['name'] == "block"):
                        self.p2_blocked = 1
                        self.p2_blocking = 1
                        self.p1_last_move = p1_data.action
                        self.p1_frame_adv = str(int(config_p1[str(abs(self.p1_last_move))]['adv']))
                        self.p2_frame_adv = str(int(config_p1[str(abs(self.p1_last_move))]['adv']) * (-1))
        
            #p2_active = p2_action['active']
            #print((self.p1_frame_counter) - time.time())
            if (p2_action['startup'] != "n/a"):
                p2_startup = int(p2_action['startup'], 0)
                if (((time.time() - self.p2_frame_counter) * 60) > p2_startup):
                    if (p1_action['name'] == "block"):
                        self.p1_blocked = 1
                        self.p1_blocking = 1
                        self.p2_last_move = p2_data.action
                        self.p1_frame_adv = str(int(config_p2[str(abs(self.p2_last_move))]['adv'])* (-1))
                        self.p2_frame_adv = str(int(config_p2[str(abs(self.p2_last_move))]['adv']))

            # if (self.p1_blocked == 0):
            #     if (p1_action['name'] == "block"):
            #         self.p1_blocked = 1
            #         self.p2_last_move = p2_data.action
            #         self.p1_frame_adv = str(int(config_p2[str(abs(self.p2_last_move))]['adv'])* (-1))
            #         self.p2_frame_adv = str(int(config_p2[str(abs(self.p2_last_move))]['adv']))

            # if (self.p2_blocked == 0):
            #     if (p2_action['name'] == "block"):
            #         self.p2_blocked = 1
            #         self.p1_last_move = p1_data.action
            #         self.p1_frame_adv = str(int(config_p1[str(abs(self.p1_last_move))]['adv']))
            #         self.p2_frame_adv = str(int(config_p1[str(abs(self.p1_last_move))]['adv']) * (-1))

            if (p1_action['name'] == "wakeup"):
                self.p1_wakeup = 1
                self.p1_frame_adv = 0

            if (p2_action['name'] == "wakeup"):
                self.p2_wakeup = 1
                self.p2_frame_adv = 0

        except KeyError:
            p1_data.actionChange = 0
            p2_data.actionChange = 0        

# def configureLabel(label_, text_):
#     label_.configure(text = text_)

def main():

    clear = lambda: os.system('cls')

    raw_data_1 = pd.read_csv(codes[p1_char] + "_vs_" + codes[p2_char] + ".csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    raw_data_2 = pd.read_csv(codes[p2_char] + "_vs_" + codes[p1_char] + ".csv", delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL, header=None)
    X_1 = raw_data_1.iloc[:, :-1].to_numpy()
    y_1 = raw_data_1.iloc[:, -1].to_numpy()
    X_2 = raw_data_2.iloc[:, :-1].to_numpy()
    y_2 = raw_data_2.iloc[:, -1].to_numpy()
    classifier_1 = LogisticRegression(random_state=0, max_iter=100000).fit(X_1, y_1)
    classifier_2 = LogisticRegression(random_state=0, max_iter=100000).fit(X_2, y_2)

    gamestate = GameState(classifier_1, classifier_2, player_side.get())

    PROCESS_VM_READ = 0x0010

    while(True):

        pid = getPID()
        if (check_pid(pid)):

            processHandle = OpenProcess(PROCESS_VM_READ, False, pid)
            base = ModuleEnumerator.GetModuleAddressByPIDandName(pid, "GGST-Win64-Shipping.exe")
            if (base is not None):
                p1_pd_char = GetValueFromAddress(processHandle, base + p1_pd.char_offset)
                p2_pd_char = GetValueFromAddress(processHandle, base + p2_pd.char_offset)

                if (((p1_pd_char > 17) or (p1_pd_char < 0)) or ((p2_pd_char > 17) or (p2_pd_char < 0))):
                    k = 0
                else:
                    p1_pd.updateData(processHandle, base, pid)
                    p2_pd.updateData(processHandle, base, pid)
                    gamestate.updateData(p1_pd, p2_pd)
                    output = gamestate.output

                    if ((p1_pd.lives_changed == 1) or (p2_pd.lives_changed == 1)):
                        # reset gamestate
                        p1_pd.lives_changed = 0
                        p2_pd.lives_changed = 0
                        gamestate = GameState(classifier_1, classifier_2, player_side.get())

main()