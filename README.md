# lightshow
control leds of a Freifunk router

## Features

* connect to Freifunk router via ssh
* turn on and off its leds

## Requirements

### Linux

* Python 3
* Pip for python 3
* Python modules : PyQT 5, pexpect, wrapt
* a FreifunkRouter

## Installation

No builds available, you gotta build it yourself for now..

### Linux

* Prepare your Freifunk router :

        make sure you get ssh access to your router

* Install python modules : 

        sudo apt-get install python3 python3-pip python3-pyqt5
        sudo pip3 install pexpect
        sudo pip3 install wrapt

* check out this repository

        cd /your/install/path
        git clone https://github.com/IARI/lightshow.git

* run 

        cd /your/install/path
        make 
  
  in the directory where you checked out the repo

## Running

### Linux

run the lightshow script from lightshow directory :

	python3 lightshow.py
	
## Scripting

In the main text window little programs can be written.
A program is a series of statements separated by horizontal whitespace.
when run, all statements will be executed in the order given.
In the following an integer n references the n'th light starting with 0
A statement can be one of the following:

        * n             toggle light n
        
        * +n, -n        turn light n on (+) rsp. off (-)
        
        * s,s...        execute statements in one step
        
        * df            set the delay between commands to f seconds where f is a float (i.e. 0.5)
        
        * gi            goto i - continue execution with the ith statement of the program
        
        * pt            print text t to console
         
        * x             terminate program
	
	
## Contact

Feel free to send an email to j.jarecki@gmx.de if you have any questions, remarks or if you find a bug.
