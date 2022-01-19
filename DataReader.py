import ctypes as c
from ctypes import wintypes as w
from subprocess import check_output
import ModuleEnumerator
import pathlib
import struct

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

def main():
    libname = pathlib.Path().absolute().name
    print(libname)
    c_lib = c.CDLL(libname)
    pid = c_lib.getProcessID("GGST-Win64-Shipping.exe")
    print(pid)

main()
