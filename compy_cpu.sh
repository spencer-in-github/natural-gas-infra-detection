#!/bin/bash
#SBATCH -J Data_download
#SBATCH -p serc
#SBATCH -n 1
#SBATCH -t 1-

ml python/3.9.0
ml py-numpy/1.24.2_py39
ml py-pandas/1.3.1_py39
ml py-pytorch/2.0.0_py39
ml py-torchvision/0.15.1_py39

python3 Data_Download.py