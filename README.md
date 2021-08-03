# ned-eval
Evaluation of Naive Exponential Dummies for the paper ["Energy-Efficient Dummy Traffic Generation for Home Automation Systems"](https://dx.doi.org/10.2478/popets-2020-0078) published at PETS 2020

The source code is licensed under the EUPL. See the LICENSING file for more information.

If you found this repository before reading the paper, you probably won't find it very useful. Best read the paper first before using this program.

## Obtaining a Dataset

The dataset used in the paper can be downloaded under [Releases](https://github.com/frederikmoellers/ned-eval/releases). You can also use your own dataset. The easiest way to use other datasets is to make them compatible with the DatabaseHandler by including the necessary tables and columns. Please refer to either the DatabaseHandler source or the sample database for reference.

## Usage

### How to Run

First, check the file `settings.py`. All configuration except for which database to use is done here. Settings are mostly self-explanatory and/or documented with comments. The sample settings file contains the values used for the paper.

Once you have a database and have configured the program to your needs, you can run the script `ned.py` (either use a Python 3 interpreter or make the file executable). The script takes one command line parameter: The database file (see "Obtaining a Dataset").

### What to expect

There's a lot of informational output and depending on your settings as well as your hardware, the runtime can vary between seconds and days. The simulation is run for all systems and all parameter sets and the output is saved in LaTeX files to be directly included in a paper.

The script computes values for epsilon-delta-unobservability for the tasks "Interact with the system within a 1h interval" and "Do not interact with the system for 1h". For the default parameters, the number of samples taken into account for the simulation is smaller than the total number of samples available. As a consequence, the script chooses a subset of the samples randomly and thus the output is slightly different every time it is run. However, the difference should not be significant.

For the sample data and default parameters, the results are (read: should be) approximately as follows:

Parameter/Dummy Traffic | System 1 | System 2.1 | System 2.2 | System 3
--- | --- | --- | --- | ---
**No dummy traffic** | _ | _ | _ | _ 
TI | 0.00 | 0.00 | 0.00 | 0.00
Epsilon | 8.77 | 7.62 | 7.83 | 7.63
Delta | 0.87 | 0.70 | 0.99 | 1.00
**Lambda = 0.001 (~1 Packets every 20 minutes)** | _ | _ | _ | _ 
TI | 0.07 | 0.02 | 1.16 | 0.08
Epsilon | 8.57 | 7.73 | 7.87 | 7.63
Delta | 0.86 | 0.70 | 0.99 | 0.99
ECI | 6.05e-4 | 7.23e-4 | 1.73e-3 | 5.57e-4
**Lambda = 0.01 (~1 Packets every 100 seconds)** | _ | _ | _ | _ 
TI | 0.67 | 0.22 | 11.73 | 0.80
Epsilon | 7.20 | 7.76 | 7.97 | 7.67
Delta | 0.79 | 0.64 | 0.90 | 0.91
ECI | 5.79e-3 | 7.95e-3 | 0.02 | 5.57e-3
**Lambda = 1/60 (~1 Packets every minute)** | _ | _ | _ | _ 
TI | 1.13 | 0.36 | 19.39 | 1.35
Epsilon | 7.08 | 7.25 | 8.19 | 7.65
Delta | 0.74 | 0.60 | 0.85 | 0.85
ECI | 0.01 | 0.01 | 0.03 | 0.01
**Lambda = 0.1 (~1 Packets every 10 seconds)** | _ | _ | _ | _ 
TI | 7.07 | 2.25 | 122.33 | 8.08
Epsilon | 5.27 | 6.74 | 6.92 | 7.50
Delta | 0.32 | 0.26 | 0.37 | 0.37
ECI | 0.06 | 0.08 | 0.18 | 0.06
**Lambda = 0.5 (~1 Packets every 2 seconds)** | _ | _ | _ | _ 
TI | 43.55 | 13.84 | 754.83 | 40.40
Epsilon | 3.91 | <e-10 | <e-10 | 3.97
Delta | 5.93e-3 | 4.78e-3 | 7.11e-3 | 6.71e-3
ECI | 0.38 | 0.50 | 1.13 | 0.28
**Lambda = 1 (~1 Packets every second)** | _ | _ | _ | _ 
TI | 115.39 | 36.69 | 1995.63 | 80.85
Epsilon | <e-10 | <e-10 | <e-10 | <e-10
Delta | 5.56e-5 | 1.46e-3 | 8.55e-4 | 7.50e-9
ECI | 1.00 | 1.33 | 2.98 | 0.56

## Theoretical considerations

The parameters Epsilon and Delta are privacy parameters for a model close to that of Differential Privacy or Private Information Retrieval. This means that smaller values are better. A value of 10^(-10) or smaller is great, a value of 1 for Delta is the worst possible result. For Epsilon, a value of 4 or less is good. For a more thorough description of the parameters, including an intuitive explanation, please refer to the paper.