# sca
## Overview
Software Compliance Analysis - A tool to identify plagiarism with Google Search

## Functionality
- Check block of code plagiarism using Google search exact match
- Generate a report in html or csv with format:
```
Target:start-end|Block|Found at
```
- Analyze match ratio with winnowing algorithm (developing)

## Usage
- sca accepts multiple inputs: folder, file, text from pipe
```
./sca.py folder/
./sca.py file
echo "text" | ./sca.py
```

## Options
```
  -h, --help            show this help message and exit
  -b BACKEND, --backend=BACKEND
                        Search backend, choose one in (google-search, google-
                        api)
  --delay=NUMBER        Delay interval per requests
  -l NUMBER, --lines=NUMBER
                        Number of lines per block
  -o OUTPUT, --output=OUTPUT
                        Name of output file
  --output-format=FORMAT
                        Output format, choose one in (csv, html), default is
                        csv
  --winnowing           Use winnow algorithm to analyze results
  --winnow-kgrams=NUMBER
                        Set noise threshold
  --winnow-winsize=NUMBER
                        Window size
  -q, --quiet           Don't print log of checking plagiarism
```
