"""Decode the original twelve-move GGB program for branch enumeration.

Run with Sage Python and PYTHONPATH=<repository>/sage. Embedded JavaScript is
never executed. Cached coordinates identify source branches only; all geometry,
scores, and target identities are recomputed exactly from the two initial points.
"""
import hashlib
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / '正17边形.ggb'
SOURCE_SHA256 = '4142700f7f7de84fa65b8546ecafd87b1abc037e6722b81fe9940b98483eb838'
# Exact lexicographic indices after mapping source A -> (0,0), B -> (1,0).
# GeoGebra's own indices are different and are not copied into the certificate.
INDICES = {'C':0,'D':1,'E':0,'F':0,'G':1,'H':1,'I':0,'J':1,'K':1,
           'L':1,'M':0,'N':1,'O':0,'P':0,'Q':1,'R':0}


def build_program():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA256
    with zipfile.ZipFile(SOURCE) as archive:
        construction = ET.fromstring(archive.read('geogebra.xml')).find('construction')
    elements = {e.get('label'):e for e in construction.findall('element')}
    outputs = {v for c in construction.findall('command') for v in c.find('output').attrib.values()}
    free_points = [n for n,e in elements.items() if e.get('type')=='point' and n not in outputs]
    assert free_points == ['A','B']
    names = {'A':'O','B':'A','c':'unit_circle'}
    program = []
    for command in construction.findall('command'):
        op = command.get('name')
        args = list(command.find('input').attrib.values())
        label = command.find('output').get('a0')
        if op == 'Angle':
            assert args == ['C','A','Q']
            continue  # Measurement only; no drawable is produced.
        if label == 'c':
            assert op == 'Circle' and args == ['A','B']
            continue  # The profile gives precisely this initial circle for free.
        identifier = 'ggb_'+label
        if op == 'Line':
            assert len(args)==2
            entry = {'id':identifier,'op':'line','through':[names[a] for a in args]}
        elif op == 'Circle':
            assert len(args)==2
            entry = {'id':identifier,'op':'circle','center':names[args[0]],'through':names[args[1]]}
        elif op == 'Intersect':
            entry = {'id':identifier,'op':'intersect','objects':[names[a] for a in args[:2]],'index':INDICES[label]}
        else:
            raise ValueError('Unexpected geometric command: '+op)
        names[label] = identifier
        program.append(entry)
    return program, elements, names
