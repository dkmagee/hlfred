#HLFRED

You must have Ureka installed on your system. Get the installer from http://ssb.stsci.edu/ureka/

##Installing superalign


####Download
	
In your browser go to https://github.com/dkmagee/superalign and click on the "Download ZIP" button on the lower right of the page.

####Compile

	cd ~/Downloads/superalign-master
	make

####Copy superalign to a place in your `PATH`

	cp superalign ~/bin

##Installing hlfred


####Download

In your browser go to https://github.com/dkmagee/hlfred and click on the "Download ZIP" button on the lower right of the page.

####Create a Ureka variant
	
	ur_setup -n hlfred

####Install

	pip install git+https://github.com/dkmagee/hlfred.git

##Running

HLFRED requires that you either have the enviroment variables `HLFRED_DSDIR` and `HLFRED_RUNDIR` set for the input and output directories or you supply them on the command line.

Here's a simple shell script to run all tasks:

	export HLFRED_DSDIR='/Volumes/DataRaid1/Data/DATASETS'
	export HLFRED_RUNDIR='/Volumes/DataRaid1/Data/REDUCED'

	hlfred dataset_name init
	hlfred dataset_name drzi
	hlfred dataset_name mcat
	hlfred dataset_name saln
	hlfred dataset_name apsh
	hlfred dataset_name drzm