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
    """ Check For the existence of a unix pid. """
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
            currentAction = ""
            previousAction = ""
            # try:
            #     currentAction = config[str(abs(self.action))]['name']
            # except KeyError:
            #     currentAction = "n/a"
            # try:
            #     previousAction = config[str(abs(temp))]['name']
            # except KeyError:
            #     previousAction = "n/a"
            # if ((currentAction != previousAction) and (currentAction != "n/a")):
            #         self.prev_action = temp
            #         self.actionChange = 1
            try:
                if (config[str(abs(self.action))]['name'] != config[str(abs(temp))]['name']):
                    self.prev_action = temp
                    self.actionChange = 1
            except KeyError:
                k = 0
        else:
            print("PID not found. The game probably isn't running.")

class GameState:

    def __init__(self, character):
        self.frame_adv = 0
        self.dist = "mid" # point blank close, mid, far (point blank is the dist at which c.S will hit)
        self.pos_adv = "neutral" # advantage, neutral, disadvantage
        # need to know dist from corner, dont currently know this info yet. will require scanning.
        self.character = character # 1, 2. from which character should the analysis be from
        self.player_last_move = -99
        self.opponent_last_move = -99
        self.player_blocked = -1
        self.opponent_blocked = -1
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

    def createSnapshot(self, player_char, opponent_char, action):
        config_player = configparser.ConfigParser()
        config_player.read(str(player_char) + '.ini')
        config_opponent = configparser.ConfigParser()
        config_opponent.read(str(opponent_char) + '.ini')
        player_last = config_player[str(abs(self.player_last_move))]['name']
        opponent_last = config_player[str(abs(self.opponent_last_move))]['name']
        if ((self.player_blocked == 0) or (opponent_last == "shimmy")):
            opponent_last = "n/a"
        if ((self.opponent_blocked == 0) or (player_last == "shimmy")):
            player_last = "n/a"
        print(str(self.character) + ": [" + str(self.frame_adv) + ", " + self.dist + ", " + self.pos_adv + ", " + player_last + ", " + opponent_last + ", " + str(action) + "]\n")
        with open(str(player_char) + '.csv', 'a', newline='') as csvfile:
           writer = csv.writer(csvfile, delimiter = ',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
           writer.writerow([str(self.frame_adv), self.dist, self.pos_adv, player_last, opponent_last, str(action)])

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
        # playerSide = ""
        # if (playerData.dist > opponentData.dist):
        #     playerSide = "right"
        # else:
        #     playerSide = "left"
        if (playerData.dist < 1500): # near left corner
            if (playerData.dist > opponentData.dist): 
                self.pos_adv = "adv"
            elif ((opponentData.dist > playerData.dist) and (opponentData.dist < 1500)):
                self.pos_adv = "disadv" 
            else:
                self.pos_adv = "neutral"
        elif (playerData.dist > 2300): # near right corner
            if (playerData.dist < opponentData.dist):
                self.pos_adv = "adv"
            elif ((opponentData.dist < playerData.dist) and (opponentData.dist > 2300)):
                self.pos_adv = "disadv"
            else:
                self.pos_adv = "neutral"
        
        config_player = configparser.ConfigParser()
        config_player.read(str(playerData.char) + '.ini')
        config_opponent = configparser.ConfigParser()
        config_opponent.read(str(opponentData.char) + '.ini')
        try:
            player_action = config_player[str(abs(playerData.action))]
            opponent_action = config_opponent[str(abs(opponentData.action))]

            if (self.opponent_blocked == 0):
                if (self.player_blocked == 0):
                    self.frame_adv = 0
                else:
                    self.frame_adv = str(int(config_opponent[str(abs(self.opponent_last_move))]['adv']) * (-1))
            else:
                self.frame_adv = str(int(config_player[str(abs(self.player_last_move))]['adv']))

            if (playerData.actionChange == 1):
                if ((player_action['name'] != "block") and (player_action['name'] != "shimmy")):
                    self.createSnapshot(playerData.char, opponentData.char, player_action['name'])
                self.opponent_blocked = 0
                self.player_blocked = 0
                playerData.actionChange = 0

            self.player_last_move = playerData.action
            self.opponent_last_move = opponentData.action

            if (player_action['name'] == "block"):
                self.player_blocked = 1
                #self.player_last_move = "n/a"
            #else:
                #self.opponent_last_move = "n/a"
                #self.player_blocked = 0
            
            if (opponent_action['name'] == "block"):
                #self.player_last_move = playerData.action
                #self.opponent_last_move = "n/a"
                self.opponent_blocked = 1
            #else:
                #self.player_last_move = "n/a"
                #self.opponent_blocked = 0
        except KeyError:
            playerData.actionChange = 0

                

def main():
    config = configparser.ConfigParser()
    config.read('addresses.ini')
    p1_pd = PlayerData(1, config['P1Data']['p1_hp_offset'], config['P1Data']['p1_tension_offset'], config['P1Data']['p1_burst_offset'], config['P1Data']['p1_dist_offset'], config['P1Data']['p1_char_offset'])
    p2_pd = PlayerData(2, config['P2Data']['p2_hp_offset'], config['P2Data']['p2_tension_offset'], config['P2Data']['p2_burst_offset'], config['P2Data']['p2_dist_offset'], config['P2Data']['p2_char_offset'])
    gamestate_1 = GameState(1)
    gamestate_2 = GameState(2)

    clear = lambda: os.system('cls')
    pid = getPID()    
    PROCESS_VM_READ = 0x0010
    processHandle = OpenProcess(PROCESS_VM_READ, False, pid)
    base = ModuleEnumerator.GetModuleAddressByPIDandName(pid, "GGST-Win64-Shipping.exe")
    old = []
    new = []
    move_config_2 = configparser.ConfigParser()
    move_config_2.read(str(p2_pd.char) + '.ini')
    clear()

    while(check_pid(pid)):
        p1_pd.updateData(processHandle, base, pid)
        p2_pd.updateData(processHandle, base, pid)
        gamestate_1.updateData(p1_pd, p2_pd)
        gamestate_2.updateData(p1_pd, p2_pd)
    return 0

main()