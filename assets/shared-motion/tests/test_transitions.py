import importlib.util
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
spec=importlib.util.spec_from_file_location('transitions',Path(__file__).resolve().parents[1]/'transitions.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Transitions(unittest.TestCase):
 def setUp(self):
  self.a=Image.new('RGB',(160,90),'#142030');self.b=Image.new('RGB',(160,90),'#f9eede')
  d=ImageDraw.Draw(self.b);d.rectangle((0,0,40,89),fill='orange');d.rectangle((120,0,159,89),fill='blue')
 def test_exact_endpoints_and_no_mutation(self):
  before=self.a.tobytes(),self.b.tobytes()
  for kind in m.KINDS:
   self.assertEqual(m.transition(self.a,self.b,0,kind=kind).tobytes(),self.a.convert('RGBA').tobytes())
   self.assertEqual(m.transition(self.a,self.b,1,kind=kind).tobytes(),self.b.convert('RGBA').tobytes())
  self.assertEqual(before,(self.a.tobytes(),self.b.tobytes()))
 def test_deterministic_opaque_and_correct_size(self):
  for kind in m.KINDS:
   for p in (.01,.25,.5,.75,.99):
    im=m.transition(self.a,self.b,p,kind=kind)
    self.assertEqual(im.size,self.a.size);self.assertEqual(im.mode,'RGBA')
    self.assertEqual(im.getchannel('A').getextrema(),(255,255))
    self.assertEqual(im.tobytes(),m.transition(self.a,self.b,p,kind=kind).tobytes())
 def test_radial_semantic_origin(self):
  im=m.transition(self.a,self.b,.2,kind='radial',origin=(0,0))
  self.assertEqual(im.getpixel((0,0)),self.b.convert('RGBA').getpixel((0,0)))
  self.assertEqual(im.getpixel((159,89)),self.a.convert('RGBA').getpixel((159,89)))
 def test_ripple_not_alias(self):
  self.assertNotEqual(m.transition(self.a,self.b,.45,kind='ripple').tobytes(),m.transition(self.a,self.b,.45,kind='radial').tobytes())
 def test_flip_does_not_mirror_incoming_content(self):
  im=m.transition(self.a,self.b,.95,kind='flip');left=im.getpixel((15,45));right=im.getpixel((145,45))
  self.assertGreater(left[0],left[2]);self.assertGreater(right[2],right[0])
 def test_all_axes_and_corner_origins(self):
  for axis in ('x','y'):
   self.assertEqual(m.transition(self.a,self.b,.3,kind='flip',axis=axis).size,self.a.size)
  for origin in ((0,0),(1,1),(0,1),(1,0)):
   self.assertEqual(m.transition(self.a,self.b,.6,origin=origin).size,self.a.size)
 def test_bad_input_no_silent_fallback(self):
  for kw in ({'kind':'magic'},{'origin':(-1,0)},{'strength':.2},{'axis':'z'},{'rings':0},{'feather':0}):
   with self.assertRaises(ValueError):m.transition(self.a,self.b,.5,**kw)
  for p in (-1,1.1,float('nan'),float('inf'),True):
   with self.assertRaises(ValueError):m.transition(self.a,self.b,p)
  with self.assertRaises(ValueError):m.transition(self.a,Image.new('RGB',(20,20)),.5)
if __name__=='__main__':unittest.main()
