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

No builds available, you gotta build it yourself atmfor now..

### Linux

* Prepare your Freifunk router :

        make sure you get root access via ssh key to your router

* Install python modules : 

        sudo aptitude install python3 python3-pip python3-pyqt5
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

Start Jack audio server and then run SuperBoucle.sh script from SuperBoucle directory :

	python3 lightshow.py
	
	
## Contact

Feel free to send an email to j.jarecki@gmx.de if you have any questions, remarks or if you find a bug.