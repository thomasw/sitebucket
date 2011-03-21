def grouper(n, l):
    ''' Split an iterable object into subgroups of size n or smaller.
    Source: http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python
    
    >>> list(grouper(3, 'abcdefg'))
    ['abc', 'def', 'g']
    '''
    for i in xrange(0, len(l), n):
        yield l[i:i+n]