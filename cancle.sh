#!/bin/bash
library_path=$(cd `dirname $0`;pwd)
cd $library_path
# 刷新redis中的token,注释即可
nohup python3 util/get_access_token.py > log/access_token.log 2>&1 &
path='conf/'
files=$(ls $path)
for filename in $files
do
   filename_noext=${filename%.*}
   echo $filename_noext
   nohup python3 cancle_seat.py --conf "$path$filename" > log/cancle_seat_"$filename_noext".log 2>&1 &
done