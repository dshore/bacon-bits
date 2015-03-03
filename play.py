#!/usr/bin/env python
import Bigrams
import argparse
import random
import sys

class Puzzle(object):

    SHORTEST_PATH = 2

    def __init__(self, game_api, distance=None, head=None, tail=None):
        self.game_api = game_api
        self.head_ = head
        self.tail_ = tail
        self.min_distance = Puzzle.SHORTEST_PATH if distance is None else distance
        self.max_distance = None if distance is None else distance

    def head(self):
        if self.head_ is None:
            self.head_ = self.game_api.random_node()
        return self.head_

    def tail(self):
        if self.tail_ is None:
            self.tail_ = self.game_api.random_node_by_distance(self.head()[0], self.min_distance, self.max_distance)
        return self.tail_

    def solution(self):
        return self.game_api.sense_path(self.game_api.shortest_paths((self.head()[0], self.tail()[0])))

    def __str__(self):
        return "Find the shortest path between '%s' and '%s':" % (self.head()[1], self.tail()[1])

class Board(object):

    HINT_LEVELS = ['None', 'Low', 'Medium', 'High']

    def __init__(self, game_api, head, tail):
        self.game_api = game_api
        self.head = head
        self.tail = tail

        self.forward_path_ = None
        self.backward_path_ = None
        self.distance_ = None
        self.hint_level_ = 0

        self.played_words_ = None
        self.move_cnt_ = 0

    def shortest_path(self):
        node = self.head
        path = [node[0]]
        while True:
            next_node = self.forward_path()[node]
            if next_node is None:
                break
            path += self.game_api.shortest_paths((node[0], next_node[0]))[1:]
            node = next_node
        return path

    def hint_level_str(self):
        return self.HINT_LEVELS[self.hint_level()]

    def hint_level(self):
        return self.hint_level_

    def increment_hint_level(self):
        self.hint_level_ = (self.hint_level_ + 1) % len(self.HINT_LEVELS)

    def solution(self):
        return self.game_api.sense_path(self.shortest_path())

    def move_cnt(self):
        return self.move_cnt_

    def node_played(self, word):
        if word in self.played_words():
            return self.played_words()[word]
        return None

    def play(self, cmd, node, after_node):

        self.move_cnt_ += 1

        if cmd == Game.ADD:
            self.insert(node, after_node)
            self.played_words()[node[1]] = node
        elif cmd == Game.MOVE:
            self.move(node, after_node)
        elif cmd == Game.DELETE:
            self.remove(node)
            del self.played_words()[node[1]]
        else:
            assert(False)

    def move(self, node, after_node):
        self.remove(node)
        self.insert(node, after_node)

    def insert(self, node, after_node):
        self.forward_path()[node] = self.forward_path()[after_node]
        self.backward_path()[node] = after_node

        self.backward_path()[self.forward_path()[after_node]] = node
        self.forward_path()[after_node] = node

    def remove(self, node):
        self.forward_path()[self.backward_path()[node]] = self.forward_path()[node]
        self.backward_path()[self.forward_path()[node]] = self.backward_path()[node]

        del self.forward_path()[node]
        del self.backward_path()[node]

    def is_empty(self):
        return self.num_played() == 0

    def num_played(self):
        return len(self.played_words())

    def played_words(self):
        """
        Returns: Dict keyed by word referencing nodes
        """
        if self.played_words_ is None:
            self.played_words_ = {}
        return self.played_words_

    def forward_path(self):
        """
        Returns: Dict keyed by node with items referencing the next node in path
        """
        if self.forward_path_ is None:
            self.forward_path_ = {}
            self.forward_path_[self.head] = self.tail
            self.forward_path_[self.tail] = None
        return self.forward_path_

    def backward_path(self):
        """
        Returns: Dict keyed by node with items referencing the previous node in path
        """
        if self.backward_path_ is None:
            self.backward_path_ = {}
            self.backward_path_[self.head] = None
            self.backward_path_[self.tail] = self.head
        return self.backward_path_

    def distance(self, ref_key):
        if self.distance_ is None:
            self.distance_ = {}
        if not ref_key in self.distance_:
            self.distance_[ref_key] = self.game_api.distance(ref_key[0], ref_key[1])
        return self.distance_[ref_key]

    def is_path_complete(self):
        for node1, node2 in self.forward_path().iteritems():
            if not node2 is None:
                if self.distance((node1[0], node2[0])) > 1:
                    return False
        return True

    def current_path(self):
        out = []
        node = self.head
        sense_path = self.game_api.sense_path(self.shortest_path(), include_homophones=False)
        index = 1
        while True:
            out.append((node, sense_path[index - 1]))

            next_node = self.forward_path()[node]
            if next_node is None:
                break

            index += 1
            for ii in range(self.distance((node[0], next_node[0])) - 1):
                out.append((None, sense_path[index - 1]))
                index += 1
            node = next_node
        return out

    def path_item_str(self, index, node, sense):
        gloss = '' 
        if self.hint_level() > self.HINT_LEVELS.index('None') :
            if self.hint_level() > self.HINT_LEVELS.index('Low') or not node is None:
                gloss = sense['gloss']
        return "%02d: %-20s %s" % (index, '--' if node is None else node[1], gloss)

    def __str__(self):
        out = []
        out.append("Move Count: %d" % (self.move_cnt()))
        out.append("Hint Level: %s" % (self.hint_level_str()))
        out.append("")
        index = 1
        for node, sense in self.current_path():
            out.append(self.path_item_str(index, node, sense))
            index += 1
        return '\n'.join(out)

class WordException(Exception):

    error_str = {
        'invalid': "'%s' is not a valid word",
        'matches_head': "'%s' matches the head word",
        'matches_tail': "'%s' matches the tail word",
        'already_played': "'%s' has already been played",
        'not_played': "'%s' has not been played"}

    def __init__(self, error, word):
        self.error = error
        self.word = word

    def __str__(self):
        return self.error_str[self.error] % self.word

class AfterWordException(WordException):
    def __init__(self, error, word):
        super(AfterWordException, self).__init__(error, word)

class Game(object):

    ADD = 0
    MOVE = 1
    DELETE = 2

    def __init__(self, mode, dbname, head_word=None, tail_word=None, read_gpickle=False, write_gpickle=False, cmd_list=None):
        self.mode = mode
        self.dbname = dbname
        self.head_word = head_word
        self.tail_word = tail_word
        self.cmd_list = cmd_list
        self.read_gpickle = read_gpickle
        self.write_gpickle = write_gpickle

        self.game_api_ = None

        self.cmd_att = {
            'a': {'code': Game.ADD, 'str': 'Add'},
            'm': {'code': Game.MOVE, 'str': 'Move'},
            'd': {'code': Game.DELETE, 'str': 'Delete'}}

        self.new()

    def node_from_word(self, word):
        node = self.game_api().node(word=word)
        if node[0] is None:
            raise WordException('invalid', word)
        return node

    def get_input_node(self, cmd, word):
        if word == self.puzzle().head()[1]:
            raise WordException('matches_head', word)

        if word == self.puzzle().tail()[1]:
            raise WordException('matches_tail', word)

        node = self.board().node_played(word)
        if node is None:
            if cmd == Game.MOVE or cmd == Game.DELETE:
                raise WordException('not_played', word)
            node = self.node_from_word(word)
        elif cmd == Game.ADD:
            raise WordException('already_played', word)

        return node

    def get_input_after_node(self, after_word):
        if after_word == self.puzzle().tail()[1]:
            raise AfterWordException('matches_tail', after_word)

        after_node = self.board().node_played(after_word)

        if after_node is None:
            if after_word == self.puzzle().head()[1]:
                return self.puzzle().head()
            raise AfterWordException('not_played', after_word)

        return after_node

    def play(self):
        board_modified = True
        while True:
            print
            if board_modified:
                print self.puzzle()
                print self.board()
            board_modified = False

            if self.is_over():
                print "Path is complete!"
                print
                break

            cmd = self.get_input(self.cmd_str())

            if cmd == 'a' or cmd == 'm' or cmd == 'd':

                att = self.cmd_att[cmd]

                if not cmd == 'a' and self.board().is_empty():
                    self.error_message("Can't %s a word, no words have been played" % (att['str'].lower()))
                    continue
                try:
                    board_modified = True
                    word = self.get_input('Enter word to %s: ' % (att['str'].lower()))
                    node = self.get_input_node(att['code'], word)
                    if not cmd == 'd':
                        after_word = self.get_input("%s '%s' after word: " % (att['str'], word))
                    self.board().play(att['code'], node, None if cmd == 'd' else self.get_input_after_node(after_word))
                except AfterWordException as exc:
                    self.error_message("Can't %s '%s' after '%s', %s" % (att['str'].lower(), word, after_word, exc))
                except WordException as exc:
                    self.error_message("Can't %s '%s', %s" % (att['str'].lower(), word, exc))

            elif cmd == 'p':
                print self.game_api().graph_str()
                board_modified = True
            elif cmd == 'x':
                self.game_api().debug()
            elif cmd == 'c':
                unplayed = []
                for node, sense in self.board().current_path()[1:-1]:
                    if node is None:
                        unplayed.append(sense['word'])
                rnd = range(len(unplayed))
                random.shuffle(rnd)
                for ii in rnd:
                    print unplayed[ii]
            elif cmd == 'h':
                self.board().increment_hint_level()
                board_modified = True
                self.note("Hint level set to '%s'" % self.board().hint_level_str())
            elif cmd == 's':
                print "\nShortest Path:\n%s" % (self.path_str(self.puzzle().solution()))
                if not self.board().is_empty():
                    print "\nCurrent Path:\n%s" % (self.path_str(self.board().solution()))
            elif cmd == 'q':
                break
            else:
                self.error_message("Invalid command '%s'" % (cmd))

    def path_str(self, sense_path):
        out = []
        for sense in sense_path:
            out.append('%-20s %-20s %s' % ('%s.%d' % (sense['word'], sense['index']), sense['link'], sense['gloss']))
        return '\n'.join(out)

    def start(self):
        cmd = 'n'
        while True:
            if cmd == 'n':
                self.new()
                self.play()
            elif cmd == 'r':
                self.reset()
                self.play()
            elif cmd == 'q':
                break
            else:
                self.error_message("Invalid command '%s'" % (cmd))
            cmd = self.get_input('Enter (n)ew puzzle, (r)eplay puzzle, or (q)uit: ')

    def is_over(self):
        return self.board().is_path_complete()

    def cmd_str(self):
        out = ['Enter (a)dd']
        if self.board().num_played() > 1:
            out.append('(m)move')
        if not self.board().is_empty():
            out.append('(d)elete')
        out.append('(p)uzzle')
        out.append('e(x)amine')
        out.append('(s)olution')
        out.append('(h)int level')
        out.append('(c)lue')
        out.append('(q)uit')
        return ', '.join(out) + ': '

    def note(self, str):
        raw_input("NOTE: " + str + " (press enter to continue)")

    def error_message(self, str):
        raw_input("ERROR: " + str + " (press enter to continue)")

    def game_api(self):
        if self.game_api_ is None:
            self.game_api_ = Bigrams.Game_API(self.dbname, read_gpickle=self.read_gpickle, write_gpickle=self.write_gpickle)
        return self.game_api_

    def puzzle(self):
        if self.puzzle_ is None:
            try:
                self.puzzle_ = Puzzle(self.game_api(),
                                      head=None if self.head_word is None else self.node_from_word(self.head_word.lower()),
                                      tail=None if self.tail_word is None else self.node_from_word(self.tail_word.lower()))
            except WordException as exc:
                sys.exit("FATAL_ERROR: %s" % (exc))

        return self.puzzle_

    def board(self):
        if self.board_ is None:
            self.board_ = Board(self.game_api(), self.puzzle().head(), self.puzzle().tail())
        return self.board_

    def reset(self):
        self.board_ = None

    def new(self):
        self.puzzle_ = None
        self.reset()

    def get_next_cmd(self):
        try:
            return self.cmd_list.pop(0)
        except IndexError:
            print 'Done. Last command reached.'
            exit(0)
            
    def get_input(self, cmd_str):
        if self.cmd_list is None:
           out = raw_input(cmd_str)
        else:
            cmd = self.get_next_cmd()
            print cmd_str + cmd
            out = cmd
        return out.lower().strip()                       

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gridded Bigram links', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--head_word', '-hw')
    parser.add_argument('--tail_word', '-tw')
    parser.add_argument('--dbname', '-d', default='grid_4x4')
    parser.add_argument('--mode', '-m', type=int, default=Bigrams.HUMAN_SOLO)
    parser.add_argument('--cmd_str', '-s')
    parser.add_argument('--cmd_file', '-c')
    parser.add_argument('--write_gpickle', '-wgp', action='store_true', help='verbose')
    parser.add_argument('--read_gpickle', '-rgp', action='store_true', help='verbose')
    args = parser.parse_args()

    cmd_list = None
    if args.cmd_str:
        cmd_list = args.cmd_str.split(',')
    if args.cmd_file:
        fp = open(args.cmd_file, 'r')
        cmd_list = []
        for line in fp:
            cmd_list.append(line[:-1])

    game = Game(args.mode,
                args.dbname,
                head_word=args.head_word,
                tail_word=args.tail_word,
                read_gpickle=args.read_gpickle,
                write_gpickle=args.write_gpickle,
                cmd_list=cmd_list)
    game.start()
