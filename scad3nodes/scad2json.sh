#!/bin/sh
file=$1
file=${file%.*}
file=${file##*/}

cp $1 tmp.scad
OpenSCAD tmp.scad -o tmp.csg
./parse < tmp.csg > ${file}.json
rm tmp.scad tmp.csg
# ./py.py ${file}.json
