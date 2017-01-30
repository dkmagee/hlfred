#HLFRED

In order to use HLFRED you must have AstroConda installed on your system. See https://astroconda.readthedocs.io/en/latest/ to install AstroConda.

##Installing superalign


####Download
	
In your browser go to https://github.com/dkmagee/superalign and click on the "Download ZIP" button on the lower right of the page.

####Compile

	cd ~/Downloads/superalign-master
	make

####Copy superalign and simplematch to a place in your `PATH`

	cp superalign ~/bin/superalign_hlfred
	cp simplematch ~/bin/simplematch

In order for HLFRED to find superalign you must name the executable `superalign_hlfred`.

##Installing hlfred


####Activate AstroConda 
	
	source activate astroconda

####Install

	pip install git+https://github.com/dkmagee/hlfred.git

##Running

HLFRED requires that you have the enviroment variables `HLFRED_DSDIR` and `HLFRED_RUNDIR` set for the input and output directories or you supply them on the command line. HLFRED will look for input data in `HLFRED_DSDIR/my_dataset_name` and will copy these data to `HLFRED_RUNDIR/my_dataset_name` and process the data in run directory.

Here's a simple shell script to run all tasks with the input data in a directory `HLFRED_DSDIR/test_hlf`:

	#!/bin/bash
	export HLFRED_DSDIR="/Volumes/DataRaid1/Data/DATASETS"
	export HLFRED_RUNDIR="/Volumes/DataRaid1/Data/REDUCED"
	DSN="test"

	## For ACS/WFC data
	# for task in init ampc amsk drzi mcat saln apsh drzm
	## For WFC3/UVIS data
	# for task in init amsk drzi mcat saln apsh drzm
	# For WFC3/IR data
	for task in init amsk ssub drzi mcat saln apsh mivm drzm
	do
		hlfred $DSN $task
		ret=$?
		if [[ $ret = 0 ]]; then
		    echo "HLFRED task ${task} completed"
		else
		    echo -e "\033[0;31mERROR: HLFRED task ${task} failed.\033[0m"
			exit 1
		fi
	done