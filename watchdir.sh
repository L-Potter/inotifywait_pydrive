#!/bin/bash
#filename watchdir.sh
path=$1
/usr/bin/inotifywait -mrq -e close_write,delete,create,attrib,moved_from,moved_to $path | #while read file; do echo "$file it is a test"; done
while read -r directory events filename; do
	echo "filename : $filename ,events :  $events , dir : $directory"
	temp=${directory:2}
	if [[ ${temp} == "" ]]; then
		newdir="root"
	else
		newdir=${temp::-1}
	fi
	if [[ ${filename:0:1} == "." ]]; then 
		#echo 'is .'
		#: equal pass in python
		:
	elif [[ ${filename: -5} == ".part" ]]; then
		:
	elif [[ ${filename: -5} == ".lock" ]]; then
	    :
	elif [[ ${filename: -1} == "~" ]]; then
        :
	elif [[ ${filename} == "credentials.json" ]]; then
		:
	elif [[ ${filename} == "4913" ]]; then
		:
	else
		echo $newdir
		python pydrive_inotifywait.py -name "$filename" -event $events -path $newdir
       	fi
done
#do
#	echo "it was rsynced"
#done
