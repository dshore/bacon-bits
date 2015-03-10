# bacon-bits

### MySQL Installation

1. create database wn_bacon
2. gzcat wn_bacon.sql.gz | mysql wn_bacon
3. create database wordnet30
4. gzcat wordnet30.sql.gz | mysql wordnet30
5. edit file mst.cfg 

### Examples:

1. ./play.py -d wn_bacon 
2. ./play.py -d wn_bacon -hw bacon -tw cruise

usage: play.py [-h] [--head_word HEAD_WORD] [--tail_word TAIL_WORD] [--dbname DBNAME] [--mode MODE]
               [--cmd_str CMD_STR] [--cmd_file CMD_FILE] [--write_gpickle] [--read_gpickle]

Gridded Bigram links

optional arguments:
  -h, --help            show this help message and exit  
  --head_word HEAD_WORD, -hw HEAD_WORD  
  --tail_word TAIL_WORD, -tw TAIL_WORD  
  --dbname DBNAME, -d DBNAME  
  --mode MODE, -m MODE  
  --cmd_str CMD_STR, -s CMD_STR  
  --cmd_file CMD_FILE, -c CMD_FILE  
  --write_gpickle, -wgp verbose (default: False)  
  --read_gpickle, -rgp  verbose (default: False)  
