import sys
ls = open('ui.py', encoding='utf-8').readlines()
l = ls[245]
print('len:', len(l))
print('repr:', repr(l))
print('ends_with_triple:', l.rstrip().endswith('"""'))
