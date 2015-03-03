#!/usr/bin/env python
import Bigrams
import argparse
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Gridded Bigram links', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('db')
parser.add_argument('row_str')
parser.add_argument('col_str')
parser.add_argument('cut_str')
# parser.add_argument('--undirected', '-u', action='store_true', help='verbose')
parser.add_argument('--progress_cnt', '-p', type=int, default=1000)
parser.add_argument('--verbose', '-v', action='store_true', help='verbose')
parser.add_argument('--exit', '-x', action='store_true', help='verbose')
args = parser.parse_args()

bi = Bigrams.Grid_Database(args.db, args.row_str, args.col_str, cut_str=args.cut_str)
bi.create_db()
print bi
bi.draw()
plt.show()
