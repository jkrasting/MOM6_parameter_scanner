#!/usr/bin/env python

import argparse
import collections
import fnmatch
import glob
import json
import os
import re
import shlex
import tarfile
import warnings

# Globals
debug = False

# For HTML
html_header = '''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
  <meta content="text/html; charset=ISO-8859-1"
 http-equiv="content-type">
  <title>MOM6 parameters</title>
</head>
'''


def parseCommandLine():
  """
  Parse the command line positional and optional arguments.
  This is the highest level procedure invoked from the very end of the script.
  """
  global debug # Declared global in order to set it

  # Arguments
  parser = argparse.ArgumentParser(description=
      '''
      MOM6param_scan.py scans MOM_parameter_doc files and summarizes configurations.
      It can also parse input.nml and logfiles for Fortran namelists.
      ''',
      epilog='Written by A.Adcroft, 2015.')
  parser.add_argument('files', type=str, nargs='+',
      help='''parameter-files/tar-files to scan.''')
  parser.add_argument('-nml','--namelist', action='store_true',
      help='scan for Fortran namelists.')
  parser.add_argument('-mnml','--mom6namelist', action='store_true',
      help='scan for Fortran namelists ignoring logfile.000000.out.')
  parser.add_argument('-log','--log', action='store_true',
      help='scan for model output in FMS log file.')
  parser.add_argument('-if','--ignore_files', action='append', default=[],
      help='file patterns to ignore when searching.')
  parser.add_argument('-m','--assume_mom6', action='store_true',
      help='assume FILE is a MOM6 parameter file. By default only MOM_parameter_doc.{all,short} are scanned.')
  parser.add_argument('-x','--exclude', action='append', default=[],
      help='parameters to exclude.')
  parser.add_argument('-fmt','--format', choices=['json', 'html'], default='json',
      help='output format.')
  parser.add_argument('-t','--transpose', action='store_true',
      help='transpose html table.')
  parser.add_argument('-d','--debug', action='store_true',
      help='turn on debugging information.')
  args = parser.parse_args()

  debug = args.debug

  main(args)

def main(args):
  """
  Does the actual work
  """

  if debug: print('main: args=',args)

  P = collections.OrderedDict()
  for file in args.files:
    if args.namelist: P[file] = Namelists(file, exclude=args.exclude, ignore_files=args.ignore_files)
    elif args.mom6namelist: 
      if len(args.ignore_files)>0: P[file] = Namelists(file, exclude=args.exclude, ignore_files=args.ignore_files)
      else: P[file] = Namelists(file, exclude=args.exclude, ignore_files=['*.000000.out'])
    elif args.log: P[file] = Log(file, exclude=args.exclude, ignore_files=args.ignore_files)
    elif args.assume_mom6: P[file] = Parameters(file, parameter_files=['*'+file], exclude=args.exclude)
    else: P[file] = Parameters(file, exclude=args.exclude)

  if args.format == 'object': return P
  elif len(P)==1:
    if args.format == 'json':
      print(P[file].json())
    elif args.format == 'html':
      print(html_header)
      print('<heading>'+file+'</heading>')
      P[file].html_table()
      print('</html>')
  elif len(P)>1:
    # Find all the keys
    allkeys = []
    for i,p in enumerate(P.values()):
      if i==0: p0 = p
      else:
        if debug: print('Comparing',p0.label,'<-->',p.label)
        diff = p0.compare(p)
        allkeys += diff.keys()
        p0 = p
    #allkeys = uniq(allkeys)
    allkeys = sorted(set(allkeys))

    # Construct a table as a dictionary of dictionaries
    table = collections.OrderedDict()
    for e,p in P.items():
      row = collections.OrderedDict()
      for k in allkeys: row[k] = p.get(k)
      table[e] = row
    if args.format == 'json':
      print(json.dumps(table, indent=2))
    elif args.format == 'html':
      print(html_header)
      print('<table>')
      print('<tr>\n<th>Parameter</th>')
      if args.transpose:
        for p in allkeys: print('<th><div>'+p+'</div></th>')
        for e in table:
          print('<tr>\n<td>'+e+'</td>')
          for p in allkeys: print('<td>'+table[e][p]+'</td>')
          print('</tr>')
      else:
        for e in table: print('<th><div>'+splitPath(e)+'</div></th>')
        for p in allkeys:
          print('<tr>\n<td>'+p+'</td>')
          for e in table: print('<td>'+table[e][p]+'</td>')
          print('</tr>')
      print('</table>')
      print('</html>')
  return P

def openParameterFile(file,parameter_files=['*MOM_parameter_doc.all', '*MOM_parameter_doc.short'],ignore_files=[]):
  """Returns python file object for a MOM_parameter_doc file, that might be inside a tar-file."""

  # Check if file is a directory to search
  if os.path.isdir(file):
    for root, dirs, _ in os.walk(file):
      matches = glob.glob(root+'/'+'*.tar')
      for pat in parameter_files:
        possible_matches = glob.glob(root+'/'+pat)
        for fm in ignore_files:
          to_ignore = [n for n in possible_matches if fnmatch.fnmatch(n, fm)]
          for ti in to_ignore: possible_matches.remove(ti)
        matches += possible_matches
        #matches += glob.glob(root+'/'+pat)
      matches = sorted(matches)
      if len(matches): return openParameterFile(matches[0], parameter_files=parameter_files, ignore_files=ignore_files)
    raise Exception('No matches found within sub-directories of '+file)
  if not os.path.isfile(file): raise Exception('Not sure of file type for '+file)

  # Open file based on file type
  (root, ext) = os.path.splitext(file)

  if ext == '.tar':
    tf = tarfile.open(file, 'r')
    for mp in parameter_files:
      member = fnmatch.filter(tf.getnames(), mp)
      for fm in ignore_files:
        to_ignore = [n for n in member if fnmatch.fnmatch(n, fm)]
        for ti in to_ignore: member.remove(ti)
      if len(member):
        if debug: print('openParameterFile: Found',member[0],'in',tf.getmember(member[0]))
        return tf.extractfile(member[0]), file + '(' + member[0] + ')', os.path.getctime(file)
  else: #if ext == '.all' or ext == '.short':
    matches = False
    for pat in parameter_files: matches = matches or fnmatch.fnmatch(file, pat)
    if matches:
      if debug: print('openParameterFile: opening',file)
      return open(file, 'r'), file, os.path.getctime(file)
  raise Exception('Unable to find a parameter file in '+file)

class Parameters(object):
  """MOM6 parameter parser"""
  def __init__(self, file, parameter_files=['*MOM_parameter_doc.all', '*MOM_parameter_doc.short'], exclude=[], ignore_files=[], model_name=None):
    self.dict = collections.OrderedDict()
    open_file, filename, ctime = openParameterFile(file, parameter_files=parameter_files, ignore_files=ignore_files)
    self.label = filename
    self.ctime = ctime
    open_file = open_file.read()
    if not isinstance(open_file, str):
      open_file = open_file.decode('utf8')
    lex = shlex.shlex(open_file)
    lex.commenters = '!'
    lex.wordchars += '.+-%'
    tokens = iter(lex)
    vals = []
    block = []
    lhs = True
    append = False
    for t in tokens:
      t = str(t)
      if t.endswith('%'):
        block.append(t)
        lhs = True
      elif t.startswith('%'):
        del block[-1]
        lhs = True
      elif (t == '=') and lhs:
        vals = []
        lhs = False
      elif (t == '=') and not lhs: raise Exception('Not lhs')
      elif lhs:
        if len(block): key = ''.join(block)+t
        else: key = t
        if model_name is not None: key = model_name+'%'+key
      elif t == ',':
        append = True
      elif append:
        vals.append(t)
        if not key in exclude: self.dict[key] = ','.join(vals)
        append = False
      else:
        vals.append(t)
        if not key in exclude: self.dict[key] = ','.join(vals)
        lhs = True
  def compare(self, other):
    """Compare parameters with another"""
    od1 = collections.OrderedDict(self.dict)
    od2 = collections.OrderedDict(other.dict)
    diff = {}
    for k,v1 in od1.items():
      v2 = od2.get(k,None)
      if v2 is None: diff[k] = (v1, None)
      else:
        if v1 != v2: diff[k] = (v1, v2)
        del od2[k]
    for k,v2 in od2.items():
      diff[k] = (None, v2)
    return diff
  def __repr__(self):
    return str(self.dict)
  def keys(self):
    return self.dict.keys()
  def get(self,key):
    return self.dict.get(key,'--')
  def json(self):
    return json.dumps(self.dict, indent=2)
  def html_table(self):
    print('<table>')
    print('<tr>\n<th>Parameter</th> <th>Value</th>')
    for k,v in self.dict.items():
      print('<tr> <td>'+k+'</td> <td>'+v+'</td> </tr>')
    print('</table>')

class Namelists(object):
  """Scans a logfile or input namelist file for Fortran namelists"""
  def __init__(self, file, parameter_files=['*.logfile.000000.out', '*logfile.*', 'input.nml', '*.nml'], exclude=[], ignore_files=[], uppercase_only=False):
    self.dict = collections.OrderedDict()
    open_file, filename, ctime = openParameterFile(file, parameter_files=parameter_files, ignore_files=ignore_files)
    self.label = filename
    self.ctime = ctime
    excludes = r'|'.join([fnmatch.translate(x) for x in exclude]) or r'$.'
    open_file = open_file.read()
    if not isinstance(open_file, str):
      open_file = open_file.decode('utf8')
    lex = shlex.shlex(open_file)
    lex.commenters = '!'
    lex.wordchars += '.+-&'
    tokens = iter(lex)
    vals = [None]
    block = []
    append = False
    in_namelist_block = False
    for t in tokens:
      # Cleanup the token
      if '\n' in t: t = re.sub('\n\s*','',t)
      if t.startswith('"'): t = "'"+t[1:]
      if t.endswith('"'): t = t[:-1]+"'"
      if len(t)>1 and t.startswith('&'):
        if uppercase_only: # Only examine uppercase namelist blocks
          if t[1:].upper() == t[1:]:
            block.append(t[1:].upper())
            in_namelist_block = True
        else:
          block.append(t[1:].lower())
          in_namelist_block = True
      elif not in_namelist_block:
        continue
      elif t == '/':
        del block[-1]
        in_namelist_block = False
      elif (t == '='):
        vals = []
        append = False
      elif (t[0].isalpha() or t[0] == '_') and len(vals)>0 and (not t in ('F','T')):
        if len(block): key = '%'.join(block)+'%'+t.lower()
        else: key = t.lower()
      elif t == ',':
        append = True
      elif append:
        vals.append(t)
        #if not key in exclude: self.dict[key] = ','.join(vals)
        if not re.match(excludes,key): self.dict[key] = ','.join(vals)
        append = False
      else:
        vals.append(t)
        #if not key in exclude: self.dict[key] = ','.join(vals)
        if not re.match(excludes,key): self.dict[key] = ','.join(vals)
  def compare(self, other):
    """Compare parameters with another"""
    od1 = collections.OrderedDict(self.dict)
    od2 = collections.OrderedDict(other.dict)
    diff = {}
    for k,v1 in od1.items():
      v2 = od2.get(k,None)
      if v2 is None: diff[k] = (v1, None)
      else:
        if v1 != v2: diff[k] = (v1, v2)
        del od2[k]
    for k,v2 in od2.items():
      diff[k] = (None, v2)
    return diff
  def __repr__(self):
    return str(self.dict)
  def keys(self):
    return self.dict.keys()
  def get(self,key):
    return self.dict.get(key,'--')
  def json(self):
    return json.dumps(self.dict, indent=2)
  def html_table(self):
    print('<table>')
    print('<tr>\n<th>Parameter</th> <th>Value</th>')
    for k,v in self.dict.items():
      print('<tr> <td>'+k+'</td> <td>'+v+'</td> </tr>')
    print('</table>')

class Log(Namelists):
  def __init__(self, file, parameter_files=['*logfile.*'], exclude=[], ignore_files=[]):
    super(Log, self).__init__(file, parameter_files=parameter_files, exclude=exclude, ignore_files=ignore_files, uppercase_only=True)

def splitPath(path):
  """Split a path into a multiple lines"""
  return '<br>/'.join(path.split('/'))[4:]

def uniq(list):
  """Returns an unsorted list with no repeated entries."""
  newlist = []
  for e in list:
    if not e in newlist: newlist.append(e)
  return newlist

# Invoke parseCommandLine(), the top-level prodedure
if __name__ == '__main__': parseCommandLine()
