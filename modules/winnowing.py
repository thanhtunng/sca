#!/usr/bin/python3
#
# Copyright (c) 2018 Agranya Singh
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# Ref: https://theory.stanford.edu/~aiken/publications/papers/sigmod03.pdf
# Customized from: https://github.com/agranya99/MOSS-winnowing-seqMatcher/blob/master/winnowing.py 

import pygments.token
import pygments.lexers
import hashlib
from modules.cleanUP import tokenize, toText

def extract_text(url):
    from urllib.request import urlopen
    from bs4 import BeautifulSoup
    import sys, inspect

    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    # kill all script and style elements
    for script in soup(["script", "style"]):
        script.extract() # rip it out

    # get text
    text = soup.get_text()
    # break into lines and remove leading and trailing space on each
    lines = (line.strip() for line in text.splitlines())
    # break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text

# sha-1 encoding is used to generate hash values
def hash(text):
    #this function generates hash values
    hashval = hashlib.sha1(text.encode('utf-8'))
    hashval = hashval.hexdigest()[-4 :]
    hashval = int(hashval, 16)  #using last 16 bits of sha-1 digest
    return hashval

# Function to form k-grams out of the cleaned up text
def kgrams(text, k = 25):
    tokenList = list(text)
    n = len(tokenList)
    kgrams = []
    for i in range(n - k + 1):
        kgram = ''.join(tokenList[i : i + k])
        hashval = hash(kgram)
        kgrams.append((kgram, hashval, i, i + k))  # k-gram, its hash value, starting and ending positions are stored
        # these help in marking the plagiarized content in the original code.
    return kgrams

# Function that returns the index at which minimum value of a given list (window) is located
def minIndex(arr):
    minI = 0
    minV = arr[0]
    n = len(arr)
    for i in range(n):
        if arr[i] < minV:
            minV = arr[i]
            minI = i
    return minI

# Form windows of hash values and use min-hash to limit the number of fingerprints
def fingerprints(arr, winSize = 4):
    arrLen = len(arr)
    prevMin = 0
    currMin = 0
    windows = []
    fingerprintList = []
    for i in range(arrLen - winSize):
        win = arr[i: i + winSize]  #forming windows
        windows.append(win)
        currMin = i + minIndex(win)
        if not currMin == prevMin:  #min value of window is stored only if it is not the same as min value of prev window
            fingerprintList.append(arr[currMin])  #reduces the number of fingerprints while maintaining guarantee
            prevMin = currMin  #refer to density of winnowing and guarantee threshold (Stanford paper)

    return fingerprintList

# Takes k-gram list as input and returns a list of only hash values
def hashList(arr):
    HL = []
    for i in arr:
        HL.append(i[1])
    return HL

# Function to check plagiarism and return plagiarized code and matched ratio
def plagiarismCheck(block, data, kVal = 4, winSize = 3):
    token1 = tokenize(block)  #from cleanUP.py
    str1 = toText(token1)
    token2 = tokenize(data)
    str2 = toText(token2)
    kGrams1 = kgrams(str1, kVal)  #stores k-grams, their hash values and positions in cleaned up text
    kGrams2 = kgrams(str2, kVal)
    HL1 = hashList(kGrams1)  #hash list derived from k-grams list
    HL2 = hashList(kGrams2)
    fpList1 = fingerprints(HL1, winSize)
    fpList2 = fingerprints(HL2, winSize)
    start = []   # To store the start values corresponding to matching fingerprints
    end = []   # To store end values
    code = block  # Original code
    plCode = ""   # Code with marked plagiarized content
    points = []
    for i in fpList1:
        for j in fpList2:
            if i == j: # fingerprints match
                flag = 0
                match = HL1.index(i)   # index of matching fingerprints in hash list, k-grams list
                newStart = kGrams1[match][2]   # start position of matched k-gram in cleaned up code
                newEnd = kGrams1[match][3]   # end position of matched k-gram in cleaned up code
                for k in token1:
                    if k[2] == newStart:   # linking positions in cleaned up code to original code
                        startx = k[1]
                        flag = 1
                    if k[2] == newEnd:
                        endx = k[1]
                if flag == 1:
                    points.append([startx, endx])
    if len(points) < 1:
        print("No fingerprints match!")
        return None, None, None
    points.sort(key = lambda x: x[0])
    points = points[1:]
    mergedPoints = []
    mergedPoints.append(points[0])
    for i in range(1, len(points)):
        last = mergedPoints[len(mergedPoints) - 1]
        if points[i][0] >= last[0] and points[i][0] <= last[1]: #merging overlapping regions
            if points[i][1] > last[1]:
                mergedPoints = mergedPoints[: len(mergedPoints)-1]
                mergedPoints.append([last[0], points[i][1]])
            else:
                pass
        else:
            mergedPoints.append(points[i])
    plCode = code[: mergedPoints[0][0]]
    plagCount = 0
    for i in range(len(mergedPoints)):
        if mergedPoints[i][1] > mergedPoints[i][0]:
            plagCount += mergedPoints[i][1] - mergedPoints[i][0]
            plCode_colored = plCode + '\x1b[6;30;42m' + code[mergedPoints[i][0] : mergedPoints[i][1]] + '\x1b[0m'
            plCode = plCode + code[mergedPoints[i][0] : mergedPoints[i][1]]
            if i < len(mergedPoints) - 1:
                plCode = plCode + code[mergedPoints[i][1] : mergedPoints[i+1][0]]
            else:
                plCode = plCode + code[mergedPoints[i][1] :]
                
    return plCode, plCode_colored, (plagCount/len(code));