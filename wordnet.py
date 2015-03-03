#!/usr/bin/env python
import Bigrams
import argparse
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Gridded Bigram links', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--src_db', '-s', default='wordnet30')
parser.add_argument('--dst_db', '-d', default='wn_bacon')
parser.add_argument('--add_relation')
parser.add_argument('--progress_cnt', '-p', type=int, default=1000)
parser.add_argument('--verbose', '-v', action='store_true', help='verbose')
parser.add_argument('--exit', '-x', action='store_true', help='verbose')
args = parser.parse_args()

bi = Bigrams.WordNet_Database(args.src_db, args.dst_db)
if args.add_relation:
    bi.add_relation(args.add_relation)
else:
    bi.create_db()
# print bi
# bi.draw()
# plt.show()
