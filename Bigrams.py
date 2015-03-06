import random
import networkx as nx
import numpy as np
import noodle as nt
import sys
import traceback

HUMAN_SOLO = 0

WORDS_SQL = """
CREATE TABLE words (
  word_id int unsigned NOT NULL AUTO_INCREMENT,
  word varchar(64) DEFAULT NULL,
  PRIMARY KEY (word_id),
  UNIQUE KEY (word)
) ENGINE=MyISAM DEFAULT CHARSET=latin1
"""

SENSES_SQL = """
CREATE TABLE senses (
  sense_id int unsigned NOT NULL AUTO_INCREMENT,
  word_id int unsigned NOT NULL,
  ref_sense_id int unsigned DEFAULT NULL,
  PRIMARY KEY (sense_id),
  UNIQUE KEY (sense_id, word_id),
  KEY (word_id),
  KEY (ref_sense_id)
) ENGINE=MyISAM DEFAULT CHARSET=latin1
"""

BIGRAMS_SQL = """
CREATE TABLE bigrams (
  bigram_id int unsigned NOT NULL AUTO_INCREMENT,
  sense1_id int unsigned NOT NULL,
  sense2_id int unsigned NOT NULL,
  link_id int unsigned NOT NULL,
  relation_id int unsigned NOT NULL,
  PRIMARY KEY (bigram_id),
  UNIQUE KEY (sense1_id, sense2_id, link_id),
  KEY (sense1_id),
  KEY (sense2_id),
  KEY (link_id),
  KEY (relation_id)
) ENGINE=MyISAM DEFAULT CHARSET=latin1
"""

LINKS_SQL = """
CREATE TABLE links (
  link_id int unsigned NOT NULL AUTO_INCREMENT,
  link varchar(64) DEFAULT NULL,
  PRIMARY KEY (link_id),
  UNIQUE KEY (link)
) ENGINE=MyISAM DEFAULT CHARSET=latin1
"""

RELATIONS_SQL = """
CREATE TABLE relations (
  relation_id int unsigned NOT NULL AUTO_INCREMENT,
  relation varchar(64) DEFAULT NULL,
  PRIMARY KEY (relation_id),
  UNIQUE KEY (relation)
) ENGINE=MyISAM DEFAULT CHARSET=latin1
"""

CONFIG_SQL = """
CREATE TABLE config (
  attribute varchar(32) NOT NULL DEFAULT '',
  value varchar(32) NOT NULL DEFAULT 'False',
  PRIMARY KEY (attribute)
) ENGINE=MyISAM DEFAULT CHARSET=latin1
"""

DIRECTED_EDGES_SQL = """
CREATE TABLE directed_edges (
  sense1_id int unsigned NOT NULL,
  sense2_id int unsigned NOT NULL,
  UNIQUE KEY (sense1_id, sense2_id)
) ENGINE=MyISAM DEFAULT CHARSET=latin1
"""

def get_database(dbname):
        
    db = Database(dbname)

    if db.get_attribute('classname') == 'Grid_Database':
        return Grid_Database(dbname, db.get_attribute('row_str'), db.get_attribute('col_str'))

    if db.get_attribute('classname') == 'WordNet_Database':
        return WordNet_Database(db.get_attribute('src_dbname'), dbname)

    return db

def word_fld(num):
    return 'word%d' % (num)

def word_id_fld(num):
    return 'word%d_id' % (num)

def sense_id_fld(num):
    return 'sense%d_id' % (num)

class Database(object):

    def __init__(self, dbname):
        self.dbname = dbname

        self.config_ = None
        self.dbh_ = None
        self.is_directed_ = None
        self.graph_ = None
        self.sense_id_first_ = None
        self.config()

    def config(self):
        if self.config_ is None:
            self.config_ = nt.Tools.config()
        return self.config_

    def dbh(self):
        if self.dbh_ is None:
            self.dbh_ = nt.SQL.connection(db=self.config().get("mysql", "default_db"),
                                          user=self.config().get("mysql", "user"),
                                          passwd=self.config().get("mysql", "passwd"),
                                          unix_socket=self.config().get("mysql", "unix_socket")
                                          )
            if self.dbh_.db_exists(self.dbname):
                self.dbh_.select_db(self.dbname)
        return self.dbh_

    def sql_tables(self):
        return [WORDS_SQL, SENSES_SQL, BIGRAMS_SQL, LINKS_SQL, CONFIG_SQL, DIRECTED_EDGES_SQL, RELATIONS_SQL]

    def create_db(self, **kwargs):
        print "NOTE: Dropping database", self.dbname
        self.dbh().drop_database(self.dbname)
        print "NOTE: Creating database", self.dbname
        self.dbh().execute('CREATE DATABASE %s' % self.dbname)
        self.dbh_ = None

        for sql in self.sql_tables():
            self.dbh().execute(sql)

        for key, val in kwargs.iteritems():
            self.dbh().execute("INSERT INTO config VALUES ('%s', '%s')" % (key, str(val)))

    def insert_into_db(self, edges=None):
        cnt = 1
        insert_cnt = 0
        for edge in edges if not edges is None else self.get_src_edges():
            insert_cnt += self.insert_bigram(edge)
            if cnt % 1000 == 0:
                print cnt, insert_cnt, edge[word_fld(1)], edge[word_fld(2)], edge['link']
            cnt += 1

    def insert_bigram(self, edge):
        sense_id = {}
        for num in [1, 2]:
            word_id = self.insert_word(edge[word_id_fld(num)], edge[word_fld(num)])
            sense_id[num] = self.insert_sense(edge[sense_id_fld(num)], word_id, edge['ref_sense_id'] if 'ref_sense_id' in edge else None)

        link_id = self.insert_link(edge['link_id'], edge['link'])
        if self.is_unique(sense_id[1], sense_id[2]):
            self.dbh().execute("INSERT IGNORE INTO bigrams (sense1_id, sense2_id, link_id, relation_id) VALUES (%d, %d, %d, %d)" %
                               (sense_id[1], sense_id[2], link_id, edge['relation_id']))
            return 1
        # return self.dbh().get_last_insert_id()
        return 0

    def sense_id_first(self):
        if self.sense_id_first_ is None:
            self.sense_id_first_ = 1
        return sense_id_first_
            
    def insert_sense(self, sense_id, word_id, ref_sense_id):
        flds = ['word_id']
        vals = [str(word_id)]
        if not ref_sense_id is None:
            flds.append('ref_sense_id')
            vals.append(str(ref_sense_id))

        if sense_id is None:
            if not self.sense_id_first_ is None:
                self.dbh().execute("INSERT INTO senses (%s) VALUES (%s)" % (','.join(flds), ','.join(vals)))
                return self.dbh().get_last_insert_id()
            sense_id = self.sense_id_first()

        flds.append('sense_id')
        vals.append(str(sense_id))
        self.dbh().execute("INSERT IGNORE INTO senses (%s) VALUES (%s)" % (','.join(flds), ','.join(vals)))
        return sense_id

    def insert_word(self, word_id, word):
        if word_id is None:
            self.dbh().execute("INSERT IGNORE INTO words (word) VALUES ('%s')" % (self.dbh().escape_string(word)))
            if not self.dbh().get_row_cnt():
                return self.get_word_id(word)
            return self.dbh().get_last_insert_id()

        self.dbh().execute("INSERT IGNORE INTO words VALUES (%d, '%s')" % (word_id, self.dbh().escape_string(word)))
        return word_id

    def insert_relation(self, relation_id, relation):
        if relation_id is None:
            self.dbh().execute("INSERT IGNORE INTO relations (relation) VALUES ('%s')" % (relation))
            if not self.dbh().get_row_cnt():
                return self.get_relation_id(relation)
            return self.dbh().get_last_insert_id()
        self.dbh().execute("INSERT IGNORE INTO relations (relation_id, relation) VALUES (%d, '%s')" % (relation_id, relation))
        return relation_id

    def remove_relations(self, relation):
        relation_id = self.get_relation_id(relation)
        if not relation_id is None:
            self.dbh().execute("DELETE FROM bigrams WHERE relation_id=%d" % (relation_id))
            # self.dbh().execute("DELETE FROM directed_edges WHERE relation_id=%d" % (relation_id))
        return relation_id

    def insert_link(self, link_id, link):
        if link_id is None:
            self.dbh().execute("INSERT IGNORE INTO links (link) VALUES ('%s')" % (link))
            if not self.dbh().get_row_cnt():
                return self.get_link_id(link)
            return self.dbh().get_last_insert_id()
        self.dbh().execute("INSERT IGNORE INTO links (link_id, link) VALUES (%d, '%s')" % (link_id, link))
        return link_id

    def is_unique(self, sense1_id, sense2_id):
        self.dbh().execute("INSERT IGNORE INTO directed_edges VALUES (%d, %d)" %
                           (sense1_id, sense2_id))
        if not self.dbh().get_row_cnt():
            return False
        if not self.is_directed():
            self.dbh().execute("INSERT IGNORE INTO directed_edges VALUES (%d, %d)" %
                               (sense2_id, sense1_id))
            if not self.dbh().get_row_cnt():
                return False
        return True

    def get_gpickle_path(self):
        return "%s.gpickle" % self.dbname

    def graph(self, read_gpickle=False, write_gpickle=False):
        if self.graph_ is None:
            if read_gpickle:
                print "NOTE: Reading graph pickle file:", self.get_gpickle_path()
                self.graph_ = nx.read_gpickle(self.get_gpickle_path())
            else:
                self.graph_ = nx.Graph() if not self.is_directed() else nx.DiGraph()

                print "NOTE: Building Graph from Edges"
                self.graph_.add_edges_from(self.get_edges(), bigrams=[])

                print "NOTE: Initializing Edge 'bigrams' list"
                for edge in self.get_edges_with_id():
                    self.graph_[edge[0]][edge[1]]['bigrams'] = []

                print "NOTE: Building Edge 'bigrams' list"
                for edge in self.get_edges_with_id():
                    self.graph_[edge[0]][edge[1]]['bigrams'].append(edge[2])

                print "NOTE: Removing sub-components"
                comp_list = nx.connected_components(self.graph_)
                comp_len = [len(comp) for comp in comp_list]
                comp_len.sort()
                max_len = comp_len[-1]

                for comp in comp_list:
                    if len(comp) < max_len:
                        self.graph_.remove_nodes_from(comp)

            assert(len(nx.connected_components(self.graph_)) == 1)

            if write_gpickle:
                print "NOTE: Writing graph pickle file:", self.get_gpickle_path()
                nx.write_gpickle(self.graph_, self.get_gpickle_path())

        return self.graph_

    def is_sense_pair(self, word_id, sense_id):
        return self.dbh().get_one("SELECT count(*) FROM senses WHERE sense_id=%d AND word_id=%d" % (sense_id, word_id))

    def get_bigram(self, bigram_id):
        return self.dbh().get_row_assoc("SELECT * FROM bigrams JOIN links USING (link_id) WHERE bigram_id=%d" % (bigram_id))

    def get_word_id(self, word):
        return self.dbh().get_one("SELECT word_id FROM words WHERE word='%s'" % (word))

    def get_word_from_sense_id(self, sense_id):
        return self.dbh().get_one("SELECT word FROM words JOIN senses USING (word_id) WHERE sense_id=%d" % (sense_id))

    def get_word(self, word_id):
        return self.dbh().get_one("SELECT word FROM words WHERE word_id=%d" % (word_id))

    def get_link_id(self, link):
        return self.dbh().get_one("SELECT link_id FROM links WHERE link='%s'" % (link))

    def get_relation_id(self, relation):
        return self.dbh().get_one("SELECT relation_id FROM relations WHERE relation='%s'" % (relation))

    def get_word_ids(self):
        return self.dbh().get_list("SELECT word_id FROM words")

    def get_edges(self):
        return self.dbh().get_all("SELECT w0.word_id, w1.word_id FROM bigrams JOIN senses s0 ON (sense1_id=s0.sense_id) JOIN senses s1 ON (sense2_id=s1.sense_id) JOIN words w0 ON (w0.word_id=s0.word_id) JOIN words w1 ON (w1.word_id=s1.word_id)")

    def get_edges_with_id(self):
        return self.dbh().get_all("SELECT w0.word_id, w1.word_id, bigram_id FROM bigrams JOIN senses s0 ON (sense1_id=s0.sense_id) JOIN senses s1 ON (sense2_id=s1.sense_id) JOIN words w0 ON (w0.word_id=s0.word_id) JOIN words w1 ON (w1.word_id=s1.word_id)")

    def get_attribute(self, attribute):
        return self.dbh().get_one("SELECT value FROM config WHERE attribute='%s'" % (attribute))

    def is_directed(self):
        if self.is_directed_ is None:
            self.is_directed_ = self.dbh().get_one("SELECT value FROM config WHERE attribute='directed'") == 'True'
        return self.is_directed_

class WordNet_Database(Database):

    RELATIONS = ['semantic', 'lexical', 'synonym', 'collocation']

    def __init__(self, src_dbname, dst_dbname):
        super(WordNet_Database, self).__init__(dst_dbname)
        self.src_dbname = src_dbname
        self.dst_dbname = dst_dbname
        self.tmp_valid_unigrams_ = None

    def create_db(self):
        super(WordNet_Database, self).create_db(classname=self.__class__.__name__, src_dbname=self.src_dbname)
        self.insert_relations(self.RELATIONS)

    def tmp_valid_unigrams(self):
        if self.tmp_valid_unigrams_ is None:
            self.tmp_valid_unigrams_ = self.dbh().get_random_name()
            # self.dbh().execute("CREATE TEMPORARY TABLE %s LIKE words" % (self.tmp_valid_unigrams_))
            self.dbh().execute("CREATE TABLE %s LIKE words" % (self.tmp_valid_unigrams_))
            self.dbh().execute("INSERT INTO %s SELECT wordid, lemma FROM %s.words WHERE NOT lemma REGEXP '[[:digit:]]' AND NOT lemma REGEXP '[/\. -]' ORDER BY wordid" %
                               (self.tmp_valid_unigrams_, self.src_dbname))
        return self.tmp_valid_unigrams_

    def get_src_word_id(self, word):
        return self.dbh().get_one("SELECT wordid FROM %s.words WHERE lemma='%s'" % (self.src_dbname, word))
        
    def get_src_sense_id(self, word):
        return self.dbh().get_one("SELECT senseid FROM %s.words JOIN %s.senses USING (wordid) WHERE lemma='%s'" % (self.src_dbname, self.src_dbname, word))
        
    def is_casedword(self, word):
        return self.dbh().get_one("SELECT NOT casedwordid IS NULL FROM %s.words JOIN %s.senses USING (wordid) WHERE lemma='%s'" % (self.src_dbname, self.src_dbname, word))

    def sense_id_first(self):
        if self.sense_id_first_ is None:
            self.sense_id_first_ = 1 + self.dbh().get_one("SELECT MAX(senseid) FROM %s.senses" % (self.src_dbname))
        return self.sense_id_first_
            
    def insert_relations(self, relations):

        for relation in relations:
            assert(relation in self.RELATIONS)

            relation_id = self.remove_relations(relation)
            if relation_id is None:
                relation_id = self.insert_relation(None, relation)

            print "INSERT_RELATIONS: ", relation
            self.insert_into_db(self.get_src_edges(relation_id, relation))

    def get_src_edges(self, relation_id, relation):

        if relation == 'semantic' or relation == 'lexical':
            return [edge for edge in self.dbh().get_all_assoc(
                "SELECT \
                ss.wordid as word1_id, \
                sw.word as word1, \
                ss.senseid as sense1_id, \
                ds.wordid as word2_id, \
                dw.word as word2, \
                ds.senseid as sense2_id, \
                linkid as link_id, \
                link, " +
                "%d as relation_id " % relation_id +
                "FROM %s.%s " % (self.src_dbname, "semlinks" if relation == 'semantic' else "lexlinks") +
                "JOIN %s.senses ss ON (synset1id=ss.synsetid) " % self.src_dbname +
                "JOIN %s.senses ds ON (synset2id=ds.synsetid) " % self.src_dbname +
                "JOIN %s sw ON (ss.wordid=sw.word_id) " % self.tmp_valid_unigrams() +
                "JOIN %s dw ON (ds.wordid=dw.word_id) " % self.tmp_valid_unigrams() +
                "JOIN %s.linktypes USING (linkid) " % self.src_dbname +
                "WHERE \
                ss.casedwordid IS NULL \
                AND \
                ds.casedwordid IS NULL \
                ")]

        edges = []

        if relation == 'synonym':
            for synsetid in self.dbh().get_list("SELECT synsetid FROM %s.synsets" % (self.src_dbname)):
                synset = self.dbh().get_all_assoc("SELECT * FROM %s.senses JOIN %s w ON (wordid=w.word_id) WHERE synsetid=%d AND casedwordid is NULL" % (self.src_dbname, self.tmp_valid_unigrams(), synsetid))
                for ii in range(len(synset) - 1):
                    for jj in range(ii + 1, len(synset)):
                        edges.append({
                            'word1_id': synset[ii]['wordid'],
                            'word1': synset[ii]['word'],
                            'sense1_id': synset[ii]['senseid'],
                            'word2_id': synset[jj]['wordid'],
                            'word2': synset[jj]['word'],
                            'sense2_id': synset[jj]['senseid'],
                            'link_id': None,
                            'link': relation,
                            'relation_id': relation_id
                            })

        if relation == 'collocation':
            for collocation in self.dbh().get_all_assoc(
                "SELECT lemma, \
                SUBSTRING_INDEX(REPLACE(lemma, '-', ' '), ' ',1) AS word1, \
                SUBSTRING_INDEX(REPLACE(lemma, '-', ' '), ' ',-1) AS word2 \
                FROM %s.words \
                WHERE lemma REGEXP '^[[:alpha:]]* [[:alpha:]]*$'"
                % (self.src_dbname)):

                cased1 = self.is_casedword(collocation['word1'])
                cased2 = self.is_casedword(collocation['word2'])

                if not (cased1 or cased2 or cased1 is None or cased2 is None):
                    edges.append({
                        'word1_id': self.get_src_word_id(collocation['word1']),
                        'word1': collocation['word1'],
                        'sense1_id': None,
                        'word2_id': self.get_src_word_id(collocation['word2']),
                        'word2': collocation['word2'],
                        'sense2_id': None,
                        'ref_sense_id': self.get_src_sense_id(collocation['lemma']),
                        'link_id': None,
                        'link': relation,
                        'relation_id': relation_id
                        })
        return edges

    def is_directed(self):
        return False

    def get_src_ref_sense_id(self, sense_id):
        ref_sense_id = self.dbh().get_one("SELECT ref_sense_id FROM senses WHERE sense_id=%d" % (sense_id))
        if ref_sense_id is None:
            return sense_id
        return ref_sense_id

    def get_gloss(self, sense_id):
        ref_sense_id = self.get_src_ref_sense_id(sense_id)
        return self.dbh().get_one("SELECT definition FROM %s.synsets JOIN %s.senses USING (synsetid) WHERE senseid=%d" %
                                  (self.src_dbname, self.src_dbname, ref_sense_id))

class Grid_Database(Database):

    def __init__(self, dbname, row_str, col_str, cut_str=None):
        super(Grid_Database, self).__init__(dbname)
        self.row_str = row_str
        self.col_str = col_str
        self.cut_str = cut_str
        self.grid_ = None

        self.positions_ = None
        self.row_step_ = None
        self.col_step_ = None

    def create_db(self):
        self.cut(self.cut_str)
        super(Grid_Database, self).create_db(classname=self.__class__.__name__,
                                             row_str=self.row_str,
                                             col_str=self.col_str,
                                             directed=False)
        self.insert_into_db()

    def cut(self, cut_str):
        if cut_str is not None:
            for cut in cut_str.split(','):
                if not cut == '':
                    nodes = [self.node_from_name(name.strip()) for name in cut.split('-')]
                    self.grid().remove_edge(nodes[0], nodes[1])

    def node_from_name(self, name):
        return (self.row_str.find(name[0]), self.col_str.find(name[1]))

    def name_from_node(self, node):
        return "%s%s" % (self.row_str[node[0]], self.col_str[node[1]])

    def get_src_edges(self):
        relation_id = self.insert_relation(None, 'spatial')
        return [{
            'word1_id': None,
            'sense1_id': None,
            'word2_id': None,
            'sense2_id': None,
            'word1': self.name_from_node(edge[0]),
            'word2': self.name_from_node(edge[1]),
            'link_id': None,
            'link': 'neighbor',
            'relation_id': relation_id
            } for edge in self.grid().edges()]

    def grid(self):
        if self.grid_ is None:
            self.grid_ = nx.grid_graph(dim=[len(self.row_str), len(self.col_str)], periodic=False)
        return self.grid_

    def draw(self):
        nx.draw(self.graph(), pos=self.positions(), labels=self.labels(), node_size=600)

    def labels(self):
        return self.dbh().get_dict("SELECT word_id, word FROM words")

    def position_from_node(self, node):
        loc = self.node_from_name(self.get_word(node))
        return np.ndarray(shape=(2,), buffer=np.array([self.col_step() * (loc[1] + 1), 1 - self.row_step() * (loc[0] + 1)]))

    def positions(self):
        if self.positions_ is None:
            self.positions_ = {}
            for node in self.graph().nodes():
                self.positions_[node] = self.position_from_node(node)
        return self.positions_

    def row_step(self):
        if self.row_step_ is None:
            self.row_step_ = 1 / float(len(self.row_str) + 1)
        return self.row_step_

    def col_step(self):
        if self.col_step_ is None:
            self.col_step_ = 1 / float(len(self.col_str) + 1)
        return self.col_step_

    def get_gloss(self, sense_id):
        word = self.get_word_from_sense_id(sense_id)
        return "row %s, column %s" % (word[0], word[1])

    def __str__(self):
        lines = []
        for row1 in range(len(self.row_str)):
            for ii in range(2 if row1 < len(self.row_str) - 1 else 1):
                line = ' ' if ii == 0 else ''
                for col1 in range(len(self.col_str)):
                    node1 = (row1, col1)
                    if ii == 0:
                        line += self.name_from_node(node1)
                        if col1 < (len(self.col_str) - 1):
                            node2 = (row1, col1 + 1)
                            separator = ' | ' if (ii == 0) and not self.graph().has_edge(self.get_word_id(self.name_from_node(node1)), self.get_word_id(self.name_from_node(node2))) else '   '
                            line += separator
                    else:
                        node2 = (row1 + 1, col1)
                        separator = '----' if not self.graph().has_edge(self.get_word_id(self.name_from_node(node1)), self.get_word_id(self.name_from_node(node2))) else  '    '
                        line += separator
                        if col1 < (len(self.col_str) - 1):
                            line += '+'
                lines.append(''.join(line))
        return '\n'.join(lines)

class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

    def code(self):
        return self.ERROR_CODE

    def trace(self, info):
        exc_type, exc_obj, exc_tb = info
        traceback.print_tb(exc_tb, file=sys.stderr)
        sys.stderr.write(str(self)+'\n')

    def __str__(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)

class PathUnknownError(Error):
    ERROR_CODE = 300
    def __init__(self, ref1, ref2):
        self.ref1 = ref1
        self.ref2 = ref2
        super(PathUnknownError, self).__init__("Path was not calculable between refs '%d' and '%d'" % (ref1, ref2))

class EdgeUnknownError(Error):
    ERROR_CODE = 310
    def __init__(self, ref1, ref2):
        self.ref1 = ref1
        self.ref2 = ref2
        super(EdgeUnknownError, self).__init__("Edge could not be determined defined by refs '%d' and '%d'" % (ref1, ref2))

class Game_API(object):

    def __init__(self, dbname, read_gpickle=False, write_gpickle=False):
        self.dbname = dbname
        self.read_gpickle = read_gpickle
        self.write_gpickle = write_gpickle
        self.db_ = None
        self.seeded_ = None
        self.paths_ = None
        self.graph_ = None

    def get_gpickle_path(self):
        return "%s.gpickle" % self.dbname

    def _graph(self):
        if self.graph_ is None:
            if self.read_gpickle:
                self.graph_ = nx.read_gpickle(self.get_gpickle_path())
            else:
                self.graph_= self._db().graph(read_gpickle=self.read_gpickle, write_gpickle=self.write_gpickle)
        return self.graph_

    def _db(self):
        if self.db_ is None:
            self.db_ = get_database(self.dbname)
        return self.db_

    def _seed(self):
        if self.seeded_ is None:
            random.seed()
            self.seeded_ = True
            
    def _get_bigram(self, ref0, ref1):
        try:
            return self._db().get_bigram(self._graph()[ref0][ref1]['bigrams'][0])
        except KeyError:
            raise EdgeUnknownError(ref0, ref1)

    def _is_sense_pair(self, word_id, sense_id):
        return self._db().is_sense_pair(word_id, sense_id)

    def _get_gloss(self, sense_id):
        return self._db().get_gloss(sense_id)

    def graph_str(self):
        return str(self._db())
        
    def debug(self):
        self._graph()
        print "Number of nodes:", len(self._graph().nodes())
        print "Number of edges:", len(self._graph().edges())
        comp_list = nx.connected_components(self._graph())
        print "Number of Connected Components:", len(comp_list)
        cnt = 1
        for refs in comp_list:
            if len(refs) < 100:
                words = []
                for ref in refs:
                    node = self.node(ref=ref)
                    words.append(node[1])
                print "%d: %s" % (cnt, words)
                cnt += 1
        
    def about(self):
        self._graph()
        out = {}
        out['nodes'] = len(self._graph().nodes())
        out['edges'] = len(self._graph().edges())
        out['components'] = len(nx.connected_components(self._graph()))
        return out

    def sense_path(self, ref_path, include_homophones=True):
        """
        List of dicts where each list item is based on linking senses of the form:
        {'word': <word>, 'index': <index>, 'link': <link>, 'gloss': <gloss>}
        """
        out = []
        ref1 = ref_path[0]
        prev_sense1_id = 0
        out.append({'word': self.node(ref=ref1)[1], 'index': 1, 'link': None, 'gloss': 'foo'})

        for ref2 in ref_path[1:]:

            bigram = self._get_bigram(ref1, ref2)
            ordered = self._is_sense_pair(ref1, bigram['sense1_id'])
            sense1_id = bigram['sense1_id'] if ordered else bigram['sense2_id']
            sense2_id = bigram['sense2_id'] if ordered else bigram['sense1_id']
            is_homophone = include_homophones and prev_sense1_id and (sense1_id != prev_sense1_id)

            if not prev_sense1_id:
                out[-1]['gloss'] = self._get_gloss(sense1_id)

            if is_homophone:
                out[-1]['link'] = 'homophone'
                out.append({'word': self.node(ref=ref1)[1], 'index': 2, 'link': None, 'gloss': self._get_gloss(sense1_id)})

            out[-1]['link'] = bigram['link']
            out.append({'word': self.node(ref=ref2)[1], 'index': 1, 'link': None, 'gloss': self._get_gloss(sense2_id)})

            ref1 = ref2
            prev_sense1_id = sense2_id

        return out

    def shortest_paths(self, key):
        if self.paths_ is None:
            self.paths_ = {}

        if key not in self.paths_:
            try:
                self.paths_[key] = nx.shortest_path(self._graph(), source=key[0], target=key[1])
            except (nx.NetworkXError, nx.NetworkXNoPath):
                raise PathUnknownError(key[0], key[1])
        return self.paths_[key]

    def node(self, ref=None, word=None):
        return (ref, self._db().get_word(ref)) if not ref is None else (self._db().get_word_id(word), word)

    def distance(self, ref1, ref2):
        return len(self.shortest_paths((ref1, ref2))) - 1

    def random_node_by_distance(self, ref, min_distance, max_distance):
        while True:
            tail = self.random_node()
            path = self.shortest_paths((ref, tail[0]))
            if len(path) > min_distance:
                if not max_distance is None:
                    tail = self.node(ref=path[min(max_distance, len(path) - 1)])
                break
        return tail

    def random_node(self):
        self._seed()
        return self.node(ref=self._graph().nodes()[random.randrange(self._graph().order())])
