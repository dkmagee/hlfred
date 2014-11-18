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


####Create a Ureka variant
	
	ur_setup -n hlfred

####Install

	pip install git+https://github.com/dkmagee/hlfred.git

##Running

HLFRED requires that you have the enviroment variables `HLFRED_DSDIR` and `HLFRED_RUNDIR` set for the input and output directories or you supply them on the command line. HLFRED will look for input data in `HLFRED_DSDIR/my_dataset_name` and will copy these data to `HLFRED_RUNDIR/my_dataset_name` and process the it in this directory.

Here's a simple shell script to run all tasks with the input data in a directory `HLFRED_DSDIR/test_hlf`:

	export HLFRED_DSDIR='/Volumes/DataRaid1/Data/DATASETS'
	export HLFRED_RUNDIR='/Volumes/DataRaid1/Data/REDUCED'
	DSN='test_hlf'

	hlfred $DSN init
	hlfred $DSN drzi
	hlfred $DSN mcat
	hlfred $DSN saln
	hlfred $DSN apsh
	hlfred $DSN drzm