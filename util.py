from __future__ import division, print_function
import sys as _sys
from collections import OrderedDict as _OrderedDict
from operator import itemgetter as _itemgetter, eq as _eq
import numpy as np

def inclusive_range(start, stop=None, step=None):
    if stop is None:
        stop = start
    if stop == start:
        return np.array([start])
    if step is None:
        step = stop - start
    return np.arange(start, stop + step/2, step)

def dist_num(table, dist):
    for num, val in enumerate(table):
        if dist < val:
            return num
    else:
        return num

try:
    from __builtin__ import execfile
except ImportError:
    def execfile(fn):
        exec(compile(open(fn).read(), fn, 'exec'))

def _itemsetter(index):
    def helper(where, value):
        where[index] = value
    return helper

_class_template = '''\
class {typename}(list):
    '{typename}({arg_list})'

    __slots__ = ()

    def __init__(self, {arg_list}):
        'Create new instance of {typename}({arg_list})'
        return _list.__init__(self, ({arg_list}))

    def __repr__(self):
        'Return a nicely formatted representation string'
        return '{typename}({repr_fmt})' % tuple(self)

{field_defs}
'''

_repr_template = '{name}=%r'

_field_template = '''\
    {name} = _property(_itemgetter({index:d}), _itemsetter({index:d}),
                       doc='Alias for field number {index:d}')
'''

def NamedList(typename, field_names, verbose=False):
    "Returns a new subclass of list with named fields."

    # Validate the field names.
    field_names = field_names.replace(',', ' ').split()
    if sorted(set(field_names)) != sorted(field_names):
        raise ValueError('Duplicate field names')

    # Fill-in the class template
    class_definition = _class_template.format(
        typename = typename,
        num_fields = len(field_names),
        arg_list = ', '.join(field_names),
        repr_fmt = ', '.join(_repr_template.format(name=name)
                             for name in field_names),
        field_defs = '\n'.join(_field_template.format(index=index, name=name)
                               for index, name in enumerate(field_names))
    )
    if verbose:
        print(class_definition)

    # Execute the template string in a temporary namespace and support
    # tracing utilities by setting a value for frame.f_globals['__name__']
    namespace = dict(_itemgetter=_itemgetter, _itemsetter=_itemsetter,
                     __name__='NamedList_%s' % typename,
                     OrderedDict=_OrderedDict, _property=property, _list=list)
    try:
        exec class_definition in namespace
    except SyntaxError as e:
        raise SyntaxError(e.message + ':\n' + class_definition)
    result = namespace[typename]

    # For pickling to work, the __module__ variable needs to be set to the frame
    # where the named tuple is created.  Bypass this step in enviroments where
    # sys._getframe is not defined (Jython for example) or sys._getframe is not
    # defined for arguments greater than 0 (IronPython).
    try:
        result.__module__ = _sys._getframe(1).f_globals.get('__name__', '__main__')
    except (AttributeError, ValueError):
        pass

    return result
