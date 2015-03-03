import Bigrams
import json
import os
import urlparse
import sys

class MissingArgError(Bigrams.Error):
    """
    Description: Exception generated when a mandatory argument is missing
    Returns: {'error': 400, 'msg': "'<arg>' is not set."}

    Examples:
    http://<remote_host>:<port>/random_node_by_distance?ref=10 (min_distance is not specified)
    """
    ERROR_CODE = 400
    def __init__(self, arg):
        self.arg = "'%s'" % arg
        if type(arg) == list:
            self.arg = ' or '.join(["'%s'" % key for key in arg])
        super(MissingArgError, self).__init__("%s is not set." % (self.arg))

class InvalidArgError(Bigrams.Error):
    """
    Description: Exception generated when the value of an argument is invalid
    Returns: {'error': 405, 'msg': "value '<value>' for arg '<arg>' is invalid."}

    Examples:
    http://<remote_host>:<port>/random_node_by_distance?ref=10&min_distance=undefined (min_distance should be an integer)
    """
    ERROR_CODE = 405
    def __init__(self, key, arg):
        super(InvalidArgError, self).__init__("value '%s' for arg '%s' is invalid." % (arg, key))

class NodeUnknownError(Bigrams.Error):
    """
    Description: Exception generated a node contains a ref or word which is null
    Returns: {'error': 410, 'msg': 'Node contains missing ref or word'}

    Examples:
    http://<remote_host>:<port>/get_node?ref=<bad_ref>
    """
    ERROR_CODE = 410
    def __init__(self):
        super(NodeUnknownError, self).__init__('Node contains missing ref or word')

class PathUnknownError(Bigrams.PathUnknownError):
    """
    Description: Exception generated when a path was not calculable
    Returns: {'error': 300, 'msg': "Path was not calculable between refs '<ref1>' and '<ref2>'"}

    Examples:
    http://<remote_host>:<port>/distace?ref1=<bad_ref>&ref2=<ref2>
    """
    pass

class EdgeUnknownError(Bigrams.EdgeUnknownError):
    """
    Description: Exception generated when an edge could not be determined
    Returns: {'error': 310, 'msg': "Edge could not be determined defined by refs '<ref1>' and '<ref2>'"}

    Examples:
    http://<remote_host>:<port>/sense_path?refs=1,2,<bad_ref>
    """
    pass

class API(Bigrams.Game_API):

    def __init__(self, dbname, read_gpickle=False):
        super(API, self).__init__(dbname, read_gpickle=read_gpickle)
        self._load_graph()

    def _load_graph(self):
        self._graph()

    def _get_page(self):
        return self.environ['PATH_INFO'][1:].split('/')[0]

    def _get_method(self):
        return getattr(self, "%s_" % (self._get_page()))

    def _args(self):
        if self.__args is None:
            self.__args = urlparse.parse_qs(self.environ['QUERY_STRING'])
        return self.__args

    def _get_arg(self, key, type=str, subtype=None, optional=False):
        # arg is not in query string
        if not key in self._args():
            if optional:
                return None
            raise MissingArgError(key)

        arg = self._args()[key][0]

        # arg is empty
        if arg == '' and not optional:
            raise MissingArgError(key)

        if type == int:
            try:
                return int(arg)
            except ValueError:
                raise InvalidArgError(key, arg)
        if type == bool:
            return arg.lower() == 'true'
        if type == list:
            if subtype == int:
                try:
                    return [int(item) for item in arg.split(',')]
                except ValueError:
                    raise InvalidArgError(key, arg)
        return arg

    def set_environ(self, environ):
        self.environ = environ

    def _application(self):
        self.__args = None

        try:
            return [ json.dumps(self._get_method()(urlparse.parse_qs(self.environ['QUERY_STRING']))) ]
        except (MissingArgError, NodeUnknownError, PathUnknownError, EdgeUnknownError, InvalidArgError) as exc:
            exc.trace(sys.exc_info())
            return [ json.dumps({'error': exc.code(), 'msg': str(exc)}) ]

    def _node_hash(self, node):
        if node[0] is None or node[1] is None:
            raise NodeUnknownError()
        return {'ref': node[0], 'word': node[1]}

    # def test_(self, args):
    #      return [{key: str(val)} for key, val in self.environ.iteritems()]

    def get_node_(self, args):
        """
        Service: get_node
        Description: Return a node (ref, word) pair by supplying either a 'ref' or a 'word'

        Args: ref(int, optional), word(str, optional)
        Returns: {'ref': ref(int), 'word': word(str)} 

        Examples:
        http://<remote_host>:<port>/get_node?ref=1234
        http://<remote_host>:<port>/get_node?word=foobar
        """
        ref = self._get_arg('ref', type=int, optional=True)
        word = self._get_arg('word', optional=True)

        if ref is None and word is None:
            raise MissingArgError(['ref', 'word'])

        return self._node_hash(self.node(ref=ref, word=word))

    def random_node_by_distance_(self, args):
        """
        Service: random_node_by_distance
        Description: Return a node (ref, word) pair that is within a certian distance from a ref

        Args: ref(int), min_distance(int), max_distance(int, optional)
        Returns: {'ref': ref(int), 'word': word(str)} 

        Examples:
        http://<remote_host>:<port>/random_node_by_distance?ref=1234&min_distance=3
        http://<remote_host>:<port>/random_node_by_distance?ref=1234&min_distance=3&max_distance=3
        """
        try:
            return self._node_hash(self.random_node_by_distance(self._get_arg('ref', type=int),
                                                                self._get_arg('min_distance', type=int),
                                                                self._get_arg('max_distance', type=int, optional=True)))
        except Bigrams.PathUnknownError as exc:
            raise PathUnknownError(exc.ref1, exc.ref2)

    def random_node_(self, args):
        """
        Service: random_node
        Description: Return a random node (ref, word) pair

        Args: None
        Returns: {'ref': ref(int), 'word': word(str)} 

        Examples:
        http://<remote_host>:<port>/random_node
        """
        return self._node_hash(self.random_node())

    def distance_(self, args):
        """
        Service: distance
        Description: Return the shortest distance between two refs

        Args: ref1(int), ref2(int)
        Returns: {'distance': distance(int)}

        Examples:
        http://<remote_host>:<port>/distance?ref1=1234&ref2=5678
        """
        try:
            return {'distance': self.distance(self._get_arg('ref1', type=int), self._get_arg('ref2', type=int))}
        except Bigrams.PathUnknownError:
            raise PathUnknownError(self._get_arg('ref1', type=int), self._get_arg('ref2', type=int))

    def shortest_path_(self, args):
        """
        Service: shortest_path
        Description: Return the shortest path between two refs

        Args: ref1(int), ref2(int)
        Returns: {'path': [ref1(int), ref_i(int), ref_j(int), ..., ref2(int)]}

        Examples:
        http://<remote_host>:<port>/shortest_path?ref1=1234&ref2=5678
        """
        try:
            return {'path': self.shortest_paths((self._get_arg('ref1', type=int), self._get_arg('ref2', type=int)))}
        except Bigrams.PathUnknownError:
            raise PathUnknownError(self._get_arg('ref1', type=int), self._get_arg('ref2', type=int))

    def sense_path_(self, args):
        """
        Service: sense_path
        Description: Return sense path given a list of refs

        Args: refs(comma separated list of ints), exclude_homophones(bool, optional, default=False)
        Returns: {'senses': {'word': word(str), 'index': index(int), 'link': linktype(str), 'gloss': gloss(str)},
                            {'word': word(str), 'index': index(int), 'link': linktype(str), 'gloss': gloss(str)},
                            ...,
                            {'word': word(str), 'index': index(int), 'link': linktype(str), 'gloss': gloss(str)}}

        Examples:
        http://<remote_host>:<port>/sense_path?refs=12,34,56,78
        http://<remote_host>:<port>/sense_path?refs=12,34,56,78&exclude_homophones=True
        """
        try:
            return {'senses': self.sense_path(self._get_arg('refs', type=list, subtype=int),
                                              include_homophones=not self._get_arg('exclude_homophones', type=bool, optional=True))}
        except Bigrams.EdgeUnknownError as exc:
            raise EdgeUnknownError(exc.ref1, exc.ref2)

    def about_(self, args):
        """
        Service: about
        Description: Return some information about the graph

        Args: None
        Returns: {'nodes': num_nodes(int), 'edges': num_edges(int), 'components': num_components(int)}

        Examples:
        http://<remote_host>:<port>/about
        """
        return self.about()
