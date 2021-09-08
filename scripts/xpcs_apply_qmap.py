#!/usr/bin/env python
import argparse
import os
from gladier_xpcs.reprocessing_tools.apply_qmap import apply_qmap

parser = argparse.ArgumentParser()
parser.add_argument('hdf', help='Path to the hdf file')
parser.add_argument('qmap', help='Path to the qmap file')
parser.add_argument('--proc-dir', help='Path to the qmap file', default=os.getcwd())
args = parser.parse_args()

apply_qmap(hdf_file=args.hdf, qmap_file=args.qmap, proc_dir=args.proc_dir)