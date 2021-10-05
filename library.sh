#!/bin/bash
library_path=$(cd `dirname $0`;pwd)
path='conf/'
files=$(ls $path)
for filename in $files
do
   filename_noext=${filename%.*}
   echo $filename_noext
   nohup  python3 library.py --conf "$path$filename" > log/library_"$filename_noext".log 2>&1 &
done

#nohup python3 library_zmr.py> library_zmr.log 2>&1 &