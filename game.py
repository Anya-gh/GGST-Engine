import ctypes as c
from ctypes import wintypes as w
from subprocess import check_output
import ModuleEnumerator
import configparser
import struct
import psutil
import math
import os
import csv

characters = ["Sol Badguy", "Ky Kiske", "May", "Axl Low", "Chipp Zanuff", "Potemkin", "Faust", "Millia Rage", "Zato-1", "Ramlethal Valentine", "Leo Whitefang", "Nagoriyuki", 
    "Giovanna", "Anji Mito", "I-No", "Goldlewis Dickinson", "Jack-O", "Happy Chaos"]

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
    # Check For the existence of a unix pid.
    return psutil.pid_exists(pid)

class PlayerData:
    
    def __init__(self, player_id, hp_offset, tension_offset, burst_offset, dist_offset, char_offset):
        self.player_id = player_id
        self.hp_offset = int(hp_offset, 0)
        self.tension_offset = int(tension_offset, 0)
        self.burst_offset = int(burst_offset, 0)
        self.dist_offset = int(dist_offset, 0)
        self.char_offset = int(char_offset, 0)
        self.hp = -1
        self.tension = -1
        self.burst = -1
        self.dist = -1
        self.char = -1
        self.action = -99
        self.prev_action = -99
        self.actionChange = -1
    
    def updateData(self, processHandle, base, pid):
        if(check_pid(pid)):
            self.hp = GetValueFromAddress(processHandle, base + self.hp_offset, isFloat=True)
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
                    self.prev_action = temp
                    self.actionChange = 1
            except KeyError:
                print()
        else:
            print("PID not found. The game probably isn't running.")

class GameState:

    def __init__(self, character):
        self.frame_adv = 0
        self.dist = "" # point blank close, mid, far (point blank is the dist at which c.S will hit)
        self.pos_adv = "" # advantage, neutral, disadvantage
        # need to know dist from corner, dont currently know this info yet. will require scanning.
        self.character = character # 1, 2. from which character should the analysis be from
        #self.player_last_move = "n/a"
        #self.opponent_last_move = "n/a"
        #self.state = "" # ground, air, wake-up, hit-stun (Idk some more as well maybe)
        # ignore for now
    
    #def createSnapshot(self, p1_data, p2_data):
    #    # copy self to file
    #    with open(str(p1_data.char) + '.csv', 'w', newline='') as csvfile:
    #       writer = csv.writer(csvfile, delimiter = ' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    #       writer.writerow([self.p1_gamestate.frame_adv, self.p1_gamestate.dist, self.p1_gamestate.pos_adv, self.p1_gamestate.player_last_move, self.p1_gamestate.opponent_last_move, self.p1_gamestate.action])
    #    with open(str(p2_data.char) + '.csv', 'w', newline='') as csvfile:
    #        writer = csv.writer(csvfile, delimiter = ' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    #        writer.writerow([self.p2_gamestate.frame_adv, self.p2_gamestate.dist, self.p2_gamestate.pos_adv, self.p2_gamestate.player_last_move, self.p2_gamestate.opponent_last_move, self.p2_gamestate.action])
    #    return 0

    def updateData(self, p1_data, p2_data):
        playerData = None
        opponentData = None
        if (self.character == 1):
            playerData = p1_data
            opponentData = p2_data
        else:
            playerData = p2_data
            opponentData = p1_data
        
        char_dist = abs(playerData.dist - opponentData.dist)
        if (char_dist < 2000):
            if (char_dist < 1200):
                if (char_dist < 500):
                    self.dist = "point blank"
                else:
                    self.dist = "close"
            else:
                self.dist = "mid"
        else:
            self.dist = "far"
        playerSide = ""
        if (playerData.dist > opponentData.dist):
            playerSide = "right"
        else:
            playerSide = "left"
        print(playerData.dist)
        print(opponentData.dist)
        
        #self.state = ""
        # look at P1Data.action to determine state
        # remember state is the state of player 1

        # only do this if actionChange is set to 1
        # if (playerData.actionChange == 1):
        # if (playerData.last_move == "block"):
        # self.frame_adv = opp_last_move.frame_adv
        # else:
        # if ()
        # self.frame_adv = 0
        

        config_player = configparser.ConfigParser()
        config_player.read(str(playerData.char) + '.ini')
        config_opponent = configparser.ConfigParser()
        config_opponent.read(str(opponentData.char) + '.ini')
        try:
            player_action = config_player[str(abs(playerData.action))]
            player_prev_action = config_player[str(abs(playerData.prev_action))]
            opponent_action = config_opponent[str(abs(opponentData.action))]
            opponent_prev_action = config_player[str(abs(opponentData.prev_action))]
            if (player_prev_action['name'] == "block"):
                adv = opponent_prev_action['adv']
                if (adv == "n/a"):
                    self.frame_adv = -99
                else:
                    self.frame_adv = str(int(opponent_prev_action['adv']) * (-1))
            elif (opponent_prev_action['name'] == "block"):
                adv = player_prev_action['adv']
                if (adv == "n/a"):
                    self.frame_adv = -99
                else:
                    self.frame_adv = str(int(player_prev_action['adv']))
        except KeyError:
            print("oops")
        #try:
        #    self.player_last_move = config_player[str(abs(playerData.prev_action))]['name']
        #except KeyError:
        #    self.player_last_move = "n/a"
        # try:
        #     self.opponent_last_move = config_opponent[str(abs(opponentData.prev_action))]['name']
        # except KeyError:
        #     self.player_last_move = "n/a"
        # try:
        #     player_action = config_player[str(abs(playerData.action))]
        #     player_prev_action = config_player[str(abs(playerData.prev_action))]
        #     opponent_action = config_opponent[str(abs(opponentData.action))]
        #     opponent_prev_action = config_player[str(abs(opponentData.prev_action))]
        #     if (player_action['name'] == "block"):
        #         self.frame_adv = str(int(opponent_action['adv']) * (-1))
        #         #self.opponent_last_move = opponent_action['name']
        #     elif (opponent_action['name'] == "block"):
        #         self.frame_adv = player_action['adv']
        #         #self.player_last_move = player_action['name']
        #     if (playerData.snapshot == 1):
        #         with open(str(playerData.char) + '.csv', 'a', newline='') as csvfile:
        #             writer = csv.writer(csvfile, delimiter = ' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        #             writer.writerow([self.frame_adv, self.dist, self.pos_adv, self.player_last_move, self.opponent_last_move, player_action['name']])
        #         playerData.snapshot = 0
        # except KeyError:
        #     self.frame_adv = -100
        # take frame data of prev_action ?
        # if (P1Data.action == xxx)
        # elif (P2Data.action == xxx)
        # update frame_adv