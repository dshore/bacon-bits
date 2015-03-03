import sys
import select

def heardEnter():
    i,o,e = select.select([sys.stdin],[],[])
    print i, o, e
    for s in i:
        if s == sys.stdin:
            input = sys.stdin.read(1)
            return True
    return False
