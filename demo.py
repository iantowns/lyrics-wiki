#!/usr/bin/env python

import urllib
import freebase
import difflib

lyricsText = "open eyes to awake wilder \nthrough the better days \n go silent see them running around \nchanging the rain \ngold is colder than ice more is \nmore than you can take \nopen your eyes oh \nout here don't you ever know better \nnow among the wild hills \nopen they lie \nfor diamond tears \nwe could ride \nif only you'd get back in time \nso open your eyes oh \nout here don't you ever know better \nI can only happen \nI \nand I want it back again \nI could only happen \nI \nand I'd want you back again \nif only you'd get back in time \nopen your eyes"
alteredLyrics = "open eyes to awake wilder \nthrough the better days \n go silent see them running around \nchanging the rain \ngold is colder than ice more is \nmore than you can take \nopen your eyes oh \nout here don't you ever know better \nnow among the wild hills \nopen they lie \nfor diamond tears \nwe could ride \nif only you'd get back in time \nso open your eyes \noh \nout here don't you ever know better \nI can only happen \nI and I want it back again \nI could only happen \nI and I'd want you back again \nif only you'd get back in time \nopen your eyes"

splitLyrics = lyricsText.splitlines()
splitAltered = alteredLyrics.splitlines()

difference = difflib.ndiff(splitLyrics, splitAltered)
#print '\n'.join(difference) +"\n\n\n"
crazy = '\n'.join(difference).splitlines()
modified = list()

counter = 0
previous = "-"
for line in crazy:
    if line:
        if line[0] == "+":
            previous = line
            line = "<span class='newer pair-"+str(counter)+"'>"+line[1:]+"</span>"
#            print line
            modified.append(line)
        elif line[0] == "-" :
            if previous != line[0]:
                counter+= 1
            modified.append(line)
            previous = line[0]
            line = "<span class='older pair-"+str(counter)+"'>"+line[1:]+"</span>"
#            print line
            modified.append(line)
        elif line[0] == "?":
            line = ""
        else:
            modified.append(line)
            

print modified
