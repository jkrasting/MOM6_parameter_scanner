[![Build Status](https://travis-ci.org/adcroft/MOM6_parameter_scanner.svg?branch=master)](https://travis-ci.org/adcroft/MOM6_parameter_scanner)


# MOM6 parameter scanner

## Usage

For parameter lists in an experiment:
```
MOM6param_scan.py <path1>MOM6_parameter_doc.all
MOM6param_scan.py <path1>/ascii/19000101.ascii_out.tar
MOM6param_scan.py <path1> 
MOM6param_scan.py -nml <path1> 
MOM6param_scan.py -html <path1> 
```

For differences between experiments:
```
MOM6param_scan.py <path1>/MOM6_parameter_doc.all <path2>/MOM6_parameter_doc.all ...
MOM6param_scan.py <path1>/ascii/19000101.ascii_out.tar <path2>/ascii/19000101.ascii_out.tar ...
MOM6param_scan.py <path1> <path2>
MOM6param_scan.py -nml <path1> <path2>
MOM6param_scan.py -html <path1> <path2>
```
