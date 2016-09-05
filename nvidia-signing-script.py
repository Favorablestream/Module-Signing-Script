#!/usr/bin/env python3

#License
'''
    MIT License

    Copyright (c) 2016 Kieran Gillibrand

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the 'Software'), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
'''
    
#Description
'''
    Nvidia Signing Script
    
    A small script which signs Nvidia's kernel modules for any installed kernel newer than the currently booted one.
    
    Will probably be run as a cron job. As of now I don't know how to run this when a new kernel is installed. Especially in a way independent of the package manager and package format.
    
    Inspired by this guide: http://www.pellegrino.link/2015/11/29/signing-nvidia-proprietary-driver-on-fedora.html and by my gist which corrects some out of date things: https://gist.github.com/Favorablestream/4b6822e14a6e1267b1c46049274c8e49
'''

#Metadata
__title__ = 'Nvidia Signing Script'
__author__ = 'Kieran Gillibrand'
__host__ = 'https://github.com/Favorablestream'
__copyright__ = 'Copyright 2016 Kieran Gillibrand'
__credits__ = []
__license__ = 'MIT License (LICENSE.txt)'
__version__ = '0.7'
__date__ = '4/09/2016'
__maintainer__ = 'Kieran Gillibrand'
__email__ = 'Kieran.Gillibrand6@gmail.com'
__status__ = 'Personal Project (in development)'

#Imports
import sys

import subprocess

import argparse

import re

import pkg_resources

#Helper methods called by other methods
def handleError (errorMessage: str, exitCode: int):
    '''
        Error handling function which displays a message and exits with an exit code (void).
    
        message (str): The message to display before exiting
        exitCode (int): The code to exit with
        
        Script Exit codes
        - 0: Success, normal exit code
        - 1: Package manager not found
        - 2: Unable to sign a kernel module
        - 3: Unable to extract the kernel version string
    '''
    
    exitCodes = ['Success, normal exit', 'Package manager not found', 'Unable to sign a kernel module', 'Unable to extract kernel version string']
    
    print (__title__ + ' Error: ' + errorMessage)
    print ()
    
    print ('Exiting with exit code: %s, %s' %(exitCode, exitCodes [exitCode]))
    
    sys.exit (exitCode)

def executeCommandWithOutput (commandName: str, commandArgs: list = []) -> str:
    '''
        Fetches a process' (terminal command usually for this project) output and decodes it as a utf-8 string (by default) (str)
        
        commandName (str): The name of the command to run
        commandArgs (list <string>) (optional): The arguments to supply to the command (-r, etc)
    '''
    
    ENCODING = 'utf-8'
    '''Encoding to use for decoding process output'''
    
    commandArgs.insert (0, commandName) #check_output () expects the command and it's arguments in the same list
    
    try:
        responseBytes = subprocess.check_output (commandArgs)
        
    #An exception is raised if the command does not exist, pass it to the caller
    except (OSError) as executeError:
        raise executeError
        
    return responseBytes.decode (ENCODING)
    
def executeCommandWithExitStatus (commandName: str, commandArgs: list = []) -> int:
    '''
        Run a command without fetching the output and piping all output streams to /dev/null and return the program exit status (int)
        
        commandName (str): The name of the command to run
        commandArgs (list <string>) (optional): The arguments to supply to the command (-r, etc)
        
        Command exit codes (that I look for)
        - 0: Successs
        - 127: Command not found (probably)
        - Anything else: Error
    '''    
    
    commandArgs.insert (0, commandName) #call () expects the command and it's arguments in the same list
                
    try:
        exitStatus = subprocess.call (args = commandArgs, stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
        
    #An exception is raised if the command does not exist, return 127 status instead
    except (OSError) as executeError:
        exitStatus = 127
        
    return exitStatus

def extractKernelVersionString (line: str) -> str:
    '''
        Extracts the kernel version (Ex: 4.7.2-201) from a line of output (str)
        Be sure to strip trailing newline with rstrip () if you are splitting multiline output on newlines so that you don't pass an empty line.
    
        line (str): The line of output to extract the version string from
    '''
    
    match = re.search ('\d+(\d+|\.|\-|[a-z]|[A-Z])+', line) #Match a digit then more digits, decimal points, or dashes
        
    if match == None:
        handleError ('Unable to extract version string for kernel line: %s' %line, 3)
            
    versionString = match.group (0)
        
    #Sometimes . or - are used as a seperator and are picked up as the last character so remove that last character if it isn't a digit or letter
    if not (versionString [-1:].isdigit () or versionString [-1:].isalpha ()):
        versionString = versionString [:-1]
            
    return versionString
    
def compareKernels (kernel1: str, kernel2: str) -> int:
    '''
        Compares two kernel version strings (ex: 4.7.2-200 vs 4.5.5).
        Returns 1 if kernel1 is newer (greater), -1 if the kernel2 is newer, and 0 if they are equal (int).
        
        kernel1 (str): The first kernel version string
        kernel2 (str): The second kernel version string
    '''

    kernel1Version = pkg_resources.parse_version (kernel1)
    kernel2Version = pkg_resources.parse_version (kernel2)
    
    if kernel1Version > kernel2Version:
        return 1
        
    elif kernel1Version < kernel2Version:
        return -1
        
    else:
        return 0
    
def signKernel (kernel: str, privateKeyPath: str, publicKeyPath: str):
    '''
        Signs the nvidia kernel modules for a kernel (void).
        
        kernel (str): The kernel whose modules to sign
        privateKeyPath (str): The path to the private key file to sign with
        publicKeyPath (str): The path to the public key file to sign with
    '''
    
    SIGN_BINARY_PATH = '/usr/src/kernels/' + kernel + '/scripts/sign-file'
    '''Path to the sign-file binary used to sign the kernel modules'''
    
    MODULES_PATH = '/usr/lib/modules/' + kernel + '/extra/nvidia/'
    '''Path to the kernel modules'''
    
    MODULE_NAMES = ['nvidia-drm.ko', 'nvidia.ko', 'nvidia-modeset.ko', 'nvidia-uvm.ko']
    '''Names of the kernel modules we will sign'''
    
    #Sign all the modules in our list or call handleError if the exit status is not 0 at any point
    for module in MODULE_NAMES:
        if executeCommandWithExitStatus (SIGN_BINARY_PATH, ['sha256', privateKeyPath, publicKeyPath, MODULES_PATH + module]) != 0:
            handleError ('Error signing kernel module: %s' %module, 2)
        
#Core methods called by main ()
def getPackageManager () -> str:
    '''
        Returns the package manager for the current system (str)
        There is no standard way to find the package manager so this function simply tests if the following are installed: rpm, dpkg, pacman
    '''
    
    #Each branch tries to run the package manager by checking it's version.
    #The package manager itself (ex: rpm) is called instead of a front end (ex: dnf) so more systems are covered
    #Each is called with the --version argument since it should be one of the fastest commands for a package manager and returns an exit status of 0.
    #Just running the package manager with no arguments usually returns an exit code of 1 in my experience even if it is installed.
    #If the package manager is not installed a status of 127 is usually returned, either way we just look for 0.
    #As is this will cause issues if multiple package managers are installed because only the first that is checked will be detected.
        
    #rpm (Red hat based systems)
    if executeCommandWithExitStatus ('rpm', ['--version']) == 0:
        return 'rpm'
        
    #dpkg (Debian based systems)
    elif executeCommandWithExitStatus ('dpkg', ['--version']) == 0:
        return 'dpkg'
        
    #pacman (Arch linux based systems)
    elif executeCommandWithExitStatus ('pacman', ['--version']) == 0:
        return 'pacman'
        
    #None of the above, sorry obscure package managers
    else:
        handleError ('Package manager could not be determined', 1)
    
def getCurrentKernel () -> str:
    '''
        Returns the current kernel version (str)
    '''
    
    unameOutput = executeCommandWithOutput ('uname', ['-r'])
    
    unameOutput.rstrip () #Single line output still contains trailing newline
    
    return extractKernelVersionString (unameOutput)
            
def getInstalledKernels (packageManager: str) -> list:
    '''
        Returns a list of the currently installed kernels (list <str>).
        Calls a command depending on the package manager to list all installed kernels.
        
        packageManager (str): The system package manager fetched by getPackageManager ()
    '''
        
    if packageManager == 'rpm':
        output = executeCommandWithOutput ('rpm', ['-qa', 'kernel'])
        
    elif packageManager == 'dpkg':
        output = executeCommandWithOutput ('dpkg', ['--list', '|', 'grep', 'linux-image'])
        
    elif packageManager == 'pacman':
        output = executeCommandWithOutput ('pacman', ['-Q', '|', 'grep', 'linux'])

    output = output.rstrip ()
    
    outputLines = output.split ('\n')
    
    kernelVersions = []
    
    for line in outputLines:
        versionString = extractKernelVersionString (line)
            
        kernelVersions.append (versionString)
        
    return kernelVersions
        
def getNewKernels (currentKernel: str, installedKernels: list) -> list:
    '''
        Returns a list of all kernels that are newer than the currently booted one or exits if no kernels are newer than the currently booted one (list <str>)
        
        currentKernel (str): The currently booted kernel
        installedKernels (list <str>): A list of all the currently installed kernels
    '''
        
    newKernels = []
    
    #Compare kernels and add them to the newKernels list if they are newer than the current 
    for installedKernel in installedKernels:        
        if compareKernels (installedKernel, currentKernel) == 1:
            newKernels.append (installedKernel)
    
    return newKernels
    
def signNewKernels (newKernels: list, privateKeyPath: str, publicKeyPath: str):
    '''
        Signs the nvidia kernel modules for every new kernel by calling signKernel () on each (void).
        
        newKernels (list <str>): A list of the new kernels to sign
        privateKeyPath (str): The path to the private key file to sign with
        publicKeyPath (str): The path to the public key file to sign with
    '''
    
    for newKernel in newKernels:
        signKernel (newKernel, privateKeyPath, publicKeyPath)
    
def main ():
    '''
        Main method for this script (void).
    '''
        
    print ()
    print ('%s - %s, %s' %(__title__, __copyright__, __license__))
    print ('Version: %s, %s' %(__version__, __date__))
    print ('%s' %__host__)
    print ()
    
    parser = argparse.ArgumentParser (description = 'Nvidia Signing Script: A small script which signs Nvidia\'s kernel modules for any installed kernel newer than the currently booted one.')
    parser.add_argument ('privateKeyFile', help = 'Your private key file for signing the kernel modules (see README for details)')
    parser.add_argument ('publicKeyFile', help = 'Your public key file for signing the kernel modules (see README for details)')
    args = parser.parse_args ()
    
    packageManager = getPackageManager ()
    
    print ('DEBUG: Package Manager: %s' %packageManager)
    
    currentKernel = getCurrentKernel ()
    
    print ('DEBUG: Current kernel: %s' %currentKernel)
    
    installedKernels = getInstalledKernels (packageManager)
    
    print ('DEBUG: Installed kernels: %s' %installedKernels)
    
    newKernels = getNewKernels (currentKernel, installedKernels)
    
    print ('DEBUG: New kernels: %s' %newKernels)
    
    signNewKernels (newKernels, args.privateKeyFile, args.publicKeyFile)
    
    print ('DEBUG: New kernels should now be signed')
    
if __name__ == '__main__':
    main ()
