src := $(wildcard *.scad)
csg := $(patsubst %.scad,%.csg,${src})
py := $(patsubst %.csg,%.py,${csg})

all: ${py} cad_files/z.py
	@echo Ready

csg: ${csg}

#z.py:hull.py
#	cp hull.py z.py

%.csg : %.scad
	openscad -o $@ $<

%.py : %.csg parse
	./parse <$< >$@ || rm -f $@

parse : parse.cpp
	c++ -std=c++17 -o bin/parse -g parse.cpp
	rm -rf bin/parse.dSYM

clean:
	rm -f ${csg} ${py} parse z.py

