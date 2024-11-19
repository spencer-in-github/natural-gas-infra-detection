#!/bin/bash
#SBATCH -J Densenet
#SBATCH -p serc --gres gpu:1
#SBATCH -c 1
#SBATCH -G 1
#SBATCH -t 1-

ml python/3.9.0
ml py-numpy/1.24.2_py39
ml py-pytorch/2.0.0_py39
ml py-torchvision/0.15.1_py39

python3 Densenet.py