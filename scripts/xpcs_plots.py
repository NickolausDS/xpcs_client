#!/usr/bin/env python
import argparse
from gladier_xpcs.tools.xpcs_plots import make_plots

parser = argparse.ArgumentParser()
parser.add_argument('hdf', help='Path to the hdf file')
args = parser.parse_args()

make_plots(args.hdf)

