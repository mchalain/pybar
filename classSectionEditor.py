#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2015 Philippe LAWRENCE
#
# This file is part of pyBar.
#    This script is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    pyBar is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pyBar; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import function
import file_tools
import gi
gi.require_version('Gtk', '3.0')
#print(gi.version_info)

from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

import cairo
#import time
import math
import classSection
import os
import sys
import xml.etree.ElementTree as ET

def arrow(cr, x, y, d, angle):
    cr.save()
    cr.translate(x, y)
    cr.rotate(-angle)
    cr.move_to(0, 0)
    cr.rel_line_to(-2*d, -d)
    cr.rel_line_to(0, 2*d)
    cr.close_path()
    cr.fill()
    cr.stroke()
    cr.restore()



def about():
    dialog = Gtk.AboutDialog()
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size("glade/logo.png", 25, 25)
    dialog.set_logo(pixbuf)
    dialog.set_program_name("Gestionnaire de sections droites")
    dialog.set_version("1.0")
    dialog.set_authors(["Philippe Lawrence"])
    #dialog.set_website(Const.SITE_URL)
    dialog.set_comments("Calcule les caractéristiques des sections droites")
    dialog.set_license("GNU-GPL")
    result = dialog.run()
    dialog.destroy()

def get_combos_list1(main):
    """retourne la liste des combo contenant des noeuds pour les onglets 2 et 3"""
    combos = []
    for elem in main.box2.get_children():
      widgets = elem.get_children()
      if len(widgets) < 4: continue # ligne non déployée
      if elem.get_name() == 'ArcWidget':
        combos.append(widgets[3])
        combos.append(widgets[5])
        combos.append(widgets[7])
      elif elem.get_name() == 'ArcWidget1':
        combos.append(widgets[3])
        combos.append(widgets[5])
      else: print('debug')

    for elem in main.box3.get_children():
      widgets = elem.get_children()
      if elem.get_name() == 'PathWidget':
        if len(widgets) < 7: continue
        for combo in widgets[3:-3]:
          combos.append(combo)
      elif elem.get_name() == 'CircleWidget':
        if len(widgets) < 5: continue
        combos.append(widgets[4])
        combos.append(widgets[6])
      elif elem.get_name() == 'CircleWidgetCR':
        if len(widgets) < 5: continue
        combos.append(widgets[4])
    return combos

def remove_combo_items(combo, deleted):
    """Supprime des éléments dans un combo"""
    model = combo.get_model()
    nodes = [i[0] for i in model]
    indices = []
    for node in deleted:
      if node in nodes:
        indices.append(nodes.index(node))
    for pos in reversed(indices):
      combo.remove(pos)

class ArcWidget(object):
  """Classe de base pour les arcs"""

  def __init__(self, name, s):
    self.id = name
    s.arcs[name] = classSection.Arc(name, 0, s.nodes)

  def add_hbox(self, main, hbox=None):
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    hbox.set_name('ArcWidget')
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)
    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_text(self.id)
    entry.connect('changed', self.on_name_update, main)
    hbox.pack_start(entry, False, False, 0)
    b= Gtk.MenuButton()
    b.set_size_request(50, 35)

    menu = Gtk.Menu()
    menuitem = Gtk.MenuItem(label="Départ Fin Centre")
    menuitem.show()
    menuitem.connect_object("activate", main.on_add_arc1, self, 1)
    menu.append(menuitem)
    menuitem = Gtk.MenuItem(label="Départ Centre Angle")
    menuitem.show()
    menuitem.connect_object("activate", main.on_add_arc1, self, 2)
    menu.append(menuitem)
    menuitem = Gtk.MenuItem(label="Départ Fin Angle")
    menuitem.set_sensitive(False)
    menuitem.show()
    menuitem.connect_object("activate", main.on_add_arc1, self, 3)
    menu.append(menuitem)
    menuitem = Gtk.MenuItem(label="Départ Rayon Angle")
    menuitem.set_sensitive(False)
    menuitem.show()
    menuitem.connect_object("activate", main.on_add_arc1, self, 4)
    menu.append(menuitem)
    menuitem = Gtk.MenuItem(label="Départ Fin Rayon")
    menuitem.set_sensitive(False)
    menuitem.show()
    menuitem.connect_object("activate", main.on_add_arc1, self, 5)
    menu.append(menuitem)

    b.set_popup(menu)
    b.show_all()
    hbox.pack_start(b, False, False, 0)
    self.hbox = hbox
    return hbox

  def on_update(self, widget, main):
    self.id = widget.get_text()

  def on_name_update(self, widget, main):
    main.modified = True
    arcs = main.s.arcs
    arc = arcs[self.id]
    new = widget.get_text()
    arc.id = new
    del(arcs[self.id])
    arcs[new] = arc
    self.id = new
    main.on_draw()

  def on_sign_update(self, widget, main):
    main.modified = True
    arcs = main.s.arcs
    arc = arcs[self.id]
    arc.sign = ['+', '-'][widget.get_active()]
    main.on_draw()

class ArcWidget1(ArcWidget):
  """Arc défini par 2 points et le centre"""

  def __init__(self, name, cat):
    self.cat = cat
    self.id = name

  def add_hbox(self, main, hbox=None):
    arcs = main.s.arcs
    arc = arcs[self.id]
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    hbox.set_name('ArcWidget1')
    if self.cat == 1:
      return self.add_hbox1(main, hbox)
    elif self.cat == 2:
      return self.add_hbox2(main, hbox)
    elif self.cat == 3:
      return self.add_hbox3(main, hbox)
    elif self.cat == 4:
      return self.add_hbox4(main, hbox)
    elif self.cat == 5:
      return self.add_hbox5(main, hbox)


  # départ, fin, centre [cat = 1]
  def add_hbox1(self, main, hbox=None):
    arcs = main.s.arcs
    arc = arcs[self.id]
    nodes = main.s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_text(self.id)
    entry.connect('changed', self.on_name_update, main)
    hbox.pack_start(entry, False, False, 0)
    start = arc.start
    end = arc.end
    center = arc.center

    label = Gtk.Label(label="Départ:")
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("start")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.start)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)
    label = Gtk.Label(label="Fin:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("end")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.end)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)

    label = Gtk.Label(label="Centre:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)

    combo = Gtk.ComboBoxText()
    combo.set_name("center")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.center)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Sens de rotation')
    if arc.sign == "-":
      button.set_active(True)
    button.connect('clicked', self.on_sign_update, main)
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Sens horaire")
    hbox.pack_start(label, False, False, 0)
    self.hbox = hbox
    return hbox

  # départ centre angle [cat = 2]
  def add_hbox2(self, main, hbox=None):
    arcs = main.s.arcs
    arc = arcs[self.id]
    nodes = main.s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_text(self.id)
    entry.connect('changed', self.on_name_update, main)
    hbox.pack_start(entry, False, False, 0)
    start = arc.start
    end = arc.end

    label = Gtk.Label(label="Départ:")
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("start")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.start)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)
    label = Gtk.Label(label="Centre:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("center")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.center)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)

    label = Gtk.Label(label="Angle:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_name("angle")
    if arc.angle is None: angle = "0"
    else: angle = function.PrintValue(arc.angle*180/math.pi)
    entry.set_text(angle)
    entry.connect('changed', self.on_data_update, main)
    hbox.pack_start(entry, False, False, 0)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Sens de rotation')
    if arc.sign == "-":
      button.set_active(True)
    button.connect('clicked', self.on_sign_update, main)
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Sens horaire")
    hbox.pack_start(label, False, False, 0)
    self.hbox = hbox
    return hbox

  # départ fin angle [cat = 3]
  def add_hbox3(self, main, hbox=None):
    arcs = main.s.arcs
    arc = arcs[self.id]
    nodes = main.s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_text(self.id)
    entry.connect('changed', self.on_name_update, main)
    hbox.pack_start(entry, False, False, 0)
    start = arc.start
    end = arc.end
    #center = arc.center

    label = Gtk.Label(label="Départ:")
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("start")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.start)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)
    label = Gtk.Label(label="Fin:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("end")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.end)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)

    label = Gtk.Label(label="Angle:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_name("a")
    if arc.angle is None: angle = "0"
    else: angle = str(arc.angle)
    entry.set_text(angle)
    entry.connect('changed', self.on_data_update, main)
    hbox.pack_start(entry, False, False, 0)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Sens de rotation')
    if arc.sign == "-":
      button.set_active(True)
    button.connect('clicked', self.on_sign_update, main)
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Sens horaire")
    hbox.pack_start(label, False, False, 0)
    self.hbox = hbox
    return hbox

  # départ rayon angle [cat = 4]
  def add_hbox4(self, main, hbox=None):
    arcs = main.s.arcs
    arc = arcs[self.id]
    nodes = main.s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_text(self.id)
    entry.connect('changed', self.on_name_update, main)
    hbox.pack_start(entry, False, False, 0)
    start = arc.start
    end = arc.end
    #center = arc.center

    label = Gtk.Label(label="Départ:")
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("start")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.start)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)
    label = Gtk.Label(label="Rayon:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)
    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_name("r")
    if arc.r is None: r = "0"
    else: r = str(arc.r)
    entry.set_text(r)
    entry.connect('changed', self.on_data_update, main)
    hbox.pack_start(entry, False, False, 0)

    label = Gtk.Label(label="Angle:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_name("a")
    if arc.angle is None: angle = "0"
    else: angle = str(arc.angle)
    entry.set_text(angle)
    entry.connect('changed', self.on_data_update, main)
    hbox.pack_start(entry, False, False, 0)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Sens de rotation')
    if arc.sign == "-":
      button.set_active(True)
    button.connect('clicked', self.on_sign_update, main)
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Sens horaire")
    hbox.pack_start(label, False, False, 0)
    self.hbox = hbox
    return hbox



  # départ fin rayon [cat = 5]
  def add_hbox5(self, main, hbox=None):
    arcs = main.s.arcs
    arc = arcs[self.id]
    nodes = main.s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_text(self.id)
    entry.connect('changed', self.on_name_update, main)
    hbox.pack_start(entry, False, False, 0)
    start = arc.start
    end = arc.end
    #center = arc.center

    label = Gtk.Label(label="Départ:")
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("start")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.start)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)
    label = Gtk.Label(label="Fin:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_name("end")
    combo.set_entry_text_column(0)
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(arc.end)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_data_update, main)
    hbox.pack_start(combo, False, False, 0)

    label = Gtk.Label(label="Rayon:")
    label.set_size_request(50, 35)
    hbox.pack_start(label, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_name("r")
    if arc.r is None: r = "0"
    else: r = str(arc.r)
    entry.set_text(r)
    entry.connect('changed', self.on_data_update, main)
    hbox.pack_start(entry, False, False, 0)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Sens de rotation')
    if arc.sign == "-":
      button.set_active(True)
    button.connect('clicked', self.on_sign_update, main)
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Sens horaire")
    hbox.pack_start(label, False, False, 0)
    self.hbox = hbox
    return hbox




  def on_data_update(self, widget, main):
    main.modified = True
    #center, r, a, end = None, None, None, None
    arcs = main.s.arcs
    arc = arcs[self.id]
    nodes = main.s.nodes
    di = {}
    widgets = self.hbox.get_children()
    di['start'] = widgets[3].get_active_text()
    widget = widgets[5]
    name = widget.get_name()
    if name == "r":
      try:
        val = float(widget.get_text().replace(',', '.'))
        di["r"] = val
      except ValueError:
        pass
    else:
      val = widget.get_active_text()
      di[name] = val
    widget = widgets[7]
    name = widget.get_name()
    if name == "r" or name == "angle":
      try:
        val = float(widget.get_text().replace(',', '.'))
        di[name] = val
      except ValueError:
        pass
    else:
      val = widget.get_active_text()
      di[name] = val
    arc.update(nodes, di)
    main.on_draw()




class ContourWidget(object):
  """Classe de base pour les contours"""

  def __init__(self, name):
    self.id = name

  def add_hbox(self, main, hbox=None):
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)
    entry = Gtk.Entry()
    entry.set_max_width_chars(3)
    entry.set_width_chars(2)
    entry.set_text(self.id)
    entry.connect('changed', self.on_update, main)
    hbox.pack_start(entry, False, False, 0)

    b= Gtk.MenuButton()
    b.set_size_request(50, 35)
    menu = Gtk.Menu()
    menuitem = Gtk.MenuItem(label="Cercle")
    menuitem.show()
    menuitem.connect_object("activate", main.on_add_circle, self)
    menu.append(menuitem)
    menuitem = Gtk.MenuItem(label="Polygone")
    menuitem.show()
    menuitem.connect_object("activate", main.on_add_poly, self)
    menu.append(menuitem)
    b.set_popup(menu)
    b.show_all()
    hbox.pack_start(b, False, False, 0)
    self.hbox = hbox
    return hbox


  def on_update(self, widget, main):
    self.id = widget.get_text()

class CircleWidget(ContourWidget):

  def __init__(self, name):
    self.id = name

  def add_hbox(self, main, hbox=None):
    s = main.s
    path = s.paths[self.id]
    nodes = s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    hbox.set_name('CircleWidget')
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Cercle :")
    label.set_size_request(70, 35)
    hbox.pack_start(label, False, False, 0)
    entry = Gtk.Entry()
    entry.set_max_width_chars(3)
    entry.set_width_chars(2)
    entry.set_text(path.id)
    entry.connect('changed', self.on_update, main)
    hbox.pack_start(entry, False, False, 0)
    label = Gtk.Label(label="Centre:")
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_entry_text_column(0)

    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(path.center)
      combo.set_active(active)
    except AttributeError:
      pass 
    except ValueError:
      pass 
    combo.connect('changed', self.on_update, main)
    hbox.pack_start(combo, False, False, 0)
    label = Gtk.Label(label="Passant par:")
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(path.point)
      combo.set_active(active)
    except AttributeError:
      pass 
    except ValueError:
      pass 
    combo.connect('changed', self.on_update, main)
    hbox.pack_start(combo, False, False, 0)
    button = Gtk.CheckButton()
    if not path.fill: button.set_active(True)
    button.set_tooltip_text('Creux')
    button.connect('clicked', self.on_update2, main)
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Creux")
    hbox.pack_start(label, False, False, 0)
    self.hbox = hbox
    return hbox

  def on_update(self, widget, main):
    s = main.s
    path = s.paths[self.id]
    main.modified = True
    nodes = s.nodes
    widgets = self.hbox.get_children()
    name = widgets[2].get_text()
    center = widgets[4].get_active_text()
    point = widgets[6].get_active_text()
    path.update(name, center, point, path.fill, nodes)
    main.on_draw()

  def on_update2(self, widget, main):
    main.modified = True
    path = main.s.paths[self.id]
    path.fill = [True, False][widget.get_active()]
    main.on_draw()

class CircleWidgetCR(ContourWidget):

  def __init__(self, name):
    self.id = name

  def add_hbox(self, main, hbox=None):
    s = main.s
    path = s.paths[self.id]
    nodes = s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    hbox.set_name('CircleWidgetCR')
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Cercle:")
    label.set_size_request(70, 35)
    hbox.pack_start(label, False, False, 0)
    entry = Gtk.Entry()
    entry.set_max_width_chars(3)
    entry.set_width_chars(2)
    entry.set_text(path.id)
    entry.connect('changed', self.on_update, main)
    hbox.pack_start(entry, False, False, 0)
    label = Gtk.Label(label="Centre:")
    hbox.pack_start(label, False, False, 0)
    combo = Gtk.ComboBoxText()
    combo.set_entry_text_column(0)

    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(path.center)
      combo.set_active(active)
    except AttributeError:
      pass 
    except ValueError:
      pass 
    combo.connect('changed', self.on_update, main)
    hbox.pack_start(combo, False, False, 0)
    label = Gtk.Label(label="Rayon:")
    hbox.pack_start(label, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(3)
    entry.set_width_chars(2)
    try:
      entry.set_text(str(path.r))
    except AttributeError:
      pass
    entry.connect('changed', self.on_update, main)
    hbox.pack_start(entry, False, False, 0)
    button = Gtk.CheckButton()
    if not path.fill: button.set_active(True)
    button.set_tooltip_text('Creux')
    button.connect('clicked', self.on_update2, main)
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Creux")
    hbox.pack_start(label, False, False, 0)
    self.hbox = hbox
    return hbox

  def on_update(self, widget, main):
    s = main.s
    path = s.paths[self.id]
    main.modified = True
    nodes = s.nodes
    widgets = self.hbox.get_children()
    name = widgets[2].get_text()
    center = widgets[4].get_active_text()
    r = widgets[6].get_text()
    try:
      r = float(r)
    except ValueError:
      r = None
    path.update(name, center, r, path.fill, nodes)
    main.on_draw()

  def on_update2(self, widget, main):
    main.modified = True
    path = main.s.paths[self.id]
    path.fill = [True, False][widget.get_active()]
    main.on_draw()


class PathWidget(ContourWidget):

  def __init__(self, name):
    self.id = name

  def add_hbox(self, main, hbox=None):
    s = main.s
    nodes = s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    arcs = list(s.arcs)
    arcs.sort()
    nodes.extend(arcs)
    if hbox is None:
      hbox = Gtk.Box(spacing=4)
    hbox.set_name('PathWidget')
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Contour :")
    label.set_size_request(70, 35)
    hbox.pack_start(label, False, False, 0)

    entry = Gtk.Entry()
    entry.set_max_width_chars(3)
    entry.set_width_chars(2)
    entry.set_text(self.id)
    entry.connect('changed', self.on_update1, main)
    hbox.pack_start(entry, False, False, 0)
    path = s.paths[self.id]
    d = path.nodes_list
    for elem in d:
      self.add_combo(hbox, nodes, main, elem)

    button = Gtk.CheckButton()
    if not path.fill: button.set_active(True)
    button.set_tooltip_text('Creux')
    button.connect('clicked', self.on_update2, main)
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Creux")
    hbox.pack_start(label, False, False, 0)
    b = Gtk.Button.new_from_icon_name('list-add', Gtk.IconSize.MENU)
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.connect('clicked', self.on_add_node, main)
    hbox.pack_start(b, False, False, 0)
    self.hbox = hbox
    return hbox

  def on_add_node(self, widget, main):
    s = main.s
    nodes = s.nodes
    nodes = list(nodes)
    nodes = [i for i in nodes if not i[0]=='_']
    nodes.sort()
    arcs = list(s.arcs)
    arcs.sort()
    nodes.extend(arcs)
    combo = self.add_combo(self.hbox, nodes, main, "")
    n = len(self.hbox.get_children())
    self.hbox.reorder_child(combo, n-4)
    self.hbox.show_all()

  def add_combo(self, hbox, nodes, main, actif):
    #if not actif in nodes: return # suppression d'éventuel noeuds absents
    combo = Gtk.ComboBoxText()
    for node in nodes:
      combo.append_text(node)
    try:
      active = nodes.index(actif)
      combo.set_active(active)
    except ValueError:
      pass 
    combo.connect('changed', self.on_update3, main)
    hbox.pack_start(combo, False, False, 0)
    return combo

  def on_update1(self, widget, main):
    main.modified = True
    new = widget.get_text()
    self.id = new
    main.on_draw()


  def on_update2(self, widget, main):
    s = main.s
    main.modified = True
    path = s.paths[self.id]
    path.fill = [True, False][widget.get_active()]
    main.on_draw()

  def on_update3(self, widget, main):
    #print("on_update3")
    main.modified = True
    s = main.s
    nodes = s.nodes
    arcs = s.arcs
    widgets = self.hbox.get_children()
    path = s.paths[self.id]
    d = []
    for widget in widgets:
      if isinstance(widget, Gtk.ComboBoxText):
        node = widget.get_active_text()
        if node is None: continue
        d.append(node)
    path.nodes_list = d
    path.calculate(nodes, arcs)
    main.on_draw()


class NodeWidget(object):
  def __init__(self, id, s):
    self.id = id
    if not id in s.nodes:
      s.nodes[id] = classSection.Node(id, "")
    

  def add_hbox(self, main):
    nodes = main.s.nodes
    node = nodes[self.id]
    hbox = Gtk.Box(spacing=4)
    button = Gtk.CheckButton()
    button.set_tooltip_text('Supprimer')
    hbox.pack_start(button, False, False, 0)
    label = Gtk.Label(label="Point")
    hbox.pack_start(label, False, False, 0)
    entry = Gtk.Entry()
    entry.set_max_width_chars(3)
    entry.set_width_chars(2)
    entry.set_text(self.id)
    entry.connect('changed', self.on_name_update, main)
    hbox.pack_start(entry, False, False, 0)
    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_text(str(node.x))
    entry.connect('changed', self.on_update2, main)
    hbox.pack_start(entry, False, False, 0)
    entry = Gtk.Entry()
    entry.set_max_width_chars(4)
    entry.set_width_chars(3)
    entry.set_text(str(node.y))
    entry.connect('changed', self.on_update2, main)
    hbox.pack_start(entry, False, False, 0)
    #button = Gtk.CheckButton()
    #hbox.pack_start(button, False, False, 0)
    self.hbox = hbox
    return hbox

  def on_name_update(self, widget, main):
    main.modified = True
    nodes = main.s.nodes
    node = nodes[self.id]
    old = node.id
    new = widget.get_text()
    node.id = new.replace('_', '')
    del(nodes[self.id])
    nodes[new] = node
    self.id = new
    combos = get_combos_list1(main)
    for combo in combos:
      function.change_elem_combo(combo, old, new)

    main.on_draw()

  def on_update2(self, widget, main):
    main.modified = True
    nodes = main.s.nodes
    arcs = main.s.arcs
    widgets = self.hbox.get_children()
    x = widgets[3].get_text().replace(',', '.')
    try:
      x = float(x)
    except:
      x = 0
    nodes[self.id].x = x
    y = widgets[4].get_text().replace(',', '.')
    try:
      y = float(y)
    except:
      y = 0
    nodes[self.id].y = y
    nodes[self.id].d = "%g,%g" % (x, y)

# mise à jour des arcs et des contours
    for name in arcs:
      a = arcs[name]
      if a is None: continue
      a.calculate(nodes)
    #for p in main.s.paths:
    #  path = main.s.paths[p]
    #  if path is None: continue
    #  path.calculate(nodes, arcs)

    main.on_draw()


class SectionWindow(object):

  def __init__(self, path=None):
    builder = self.builder = Gtk.Builder()
    builder.add_from_file("glade/section.glade")
    builder.connect_signals(self)
    self.window = window = builder.get_object("window1")
    self.sw = builder.get_object("scrolledwindow1")
    self.area = builder.get_object("drawingarea")
    self.notebook = builder.get_object("notebook1")
    self.box1 = builder.get_object("box1")
    self.box2 = builder.get_object("box2")
    self.box3 = builder.get_object("box3")
    self.textview = builder.get_object("textview")
    parse, color = Gdk.Color.parse('white')
    self.area.modify_bg(Gtk.StateType.NORMAL, color) 
    self.margin = 80

    self.area.connect("size-allocate", self.configure_first_page)
    self.area.connect("draw", self.on_expose)
    window.show_all()
    if path is None:
      self.on_new()
    else:
      self.on_open(None, path)

    #action = Gio.SimpleAction.new("arc1", None)
    #action.connect("activate", self.arc1_callback)
    #self.window.add_action(action)

    #action = Gio.SimpleAction.new("arc2", None)
    #action.connect("activate", self.arc2_callback)
    #self.window.add_action(action)


  def ini_box(self):
    nodes =  self.s.nodes
    for elem in self.box1.get_children():
      self.box1.remove(elem)
    for elem in self.box2.get_children():
      self.box2.remove(elem)
    for elem in self.box3.get_children():
      self.box3.remove(elem)
    li_nodes = list(nodes)
    li_nodes.sort()
    for node in li_nodes:
      if node[0] == '_': continue
      Node = nodes[node]
      Obj = NodeWidget(Node.id, self.s)
      hbox = Obj.add_hbox(self)
      self.box1.pack_start(hbox, False, False, 0)
    for node in self.s.arcs:
      a = self.s.arcs[node]
      Obj = ArcWidget1(a.id, a.cat)
      hbox = Obj.add_hbox(self)
      self.box2.pack_start(hbox, False, False, 0)
    for name in self.s.paths:
      path = self.s.paths[name]
      if isinstance(path, classSection.Path):
        Obj = PathWidget(name)
      elif isinstance(path, classSection.CirclePathCP):
        Obj = CircleWidget(name)
      else:
        Obj = CircleWidgetCR(name)
      hbox = Obj.add_hbox(self)
      self.box3.pack_start(hbox, False, False, 0)

    self.box1.show_all()
    self.box2.show_all()
    self.box3.show_all()

      

  def ini_xml(self):
    """Initialise la structure xml des données"""
    string = """<xml><nodes /></xml>"""
    return ET.ElementTree(ET.fromstring(string))

  def get_xml(self):
    xml = self.ini_xml()
    nodes =  self.s.nodes
    li_nodes = list(nodes)
    li_nodes.sort()
    for name in li_nodes:
      if name[0] == '_': continue
      Node = nodes[name]
      Node.set_xml(xml)
    arcs =  self.s.arcs
    li_arcs = list(arcs)
    li_arcs.sort()
    for name in li_arcs:
      a = arcs[name]
      a.set_xml(xml)
    for name in self.s.paths:
      Node = self.s.paths[name]
      if Node is None: continue
      Node.set_xml(xml)
    root = xml.getroot()
    return ET.tostring(root).decode()
    

  def on_switch_page(self, widget, box, n_page):
    if n_page == 3: 
      self.write_resu()

  def on_draw(self, widget=None):
    GLib.idle_add(self.update_drawing)

  def on_run(self, widget):
    self.modified = False
    xml = self.get_xml()
    self.s = classSection.StringAnalyser(xml)
    self.write_resu()
    GLib.idle_add(self.update_drawing)

  def update_drawing(self):
    #print("update_drawing")
    # Suppression des path :: optimiser mieux? modif 22 mai 2022
    for p in self.s.paths:
      path = self.s.paths[p]
      if path is None: continue
      path.calculate(self.s.nodes, self.s.arcs)
    # ----------
    x0 = self.x0
    y0 = self.y0
    w = self.w - 2*self.margin
    h = self.h - 2*self.margin
    cr = cairo.Context(self.surface)
    self.draw_surface_bg(cr)
    if hasattr(self, 's'):
      self.p1 = self.CairoDraw(cr, x0, y0, w, h)

    GLib.idle_add(self.area.queue_draw)

  def write_resu(self):
    text = self.s.print2term(False)
    textbuffer = self.textview.get_buffer()
    textbuffer.set_text(text)



  def send_data(self):
    data = self.s.set_data()
    #print("send_data", data)
    return data

  def on_open(self, widget, path=None):
    self.modified = False
    if path is None:
      path = file_tools.file_selection("", self.window, ext="xml")
    if path is None:
      return
    self.path = path
    
    if os.path.isfile(self.path):
      self.s = classSection.FileAnalyser(path)
    else:
      self.s = classSection.NewAnalyser()
      print("Impossible d'ouvrir le fichier")
    self.ini_box()
    self.write_resu()
    GLib.idle_add(self.update_drawing)

  def on_new(self, widget=None):
    self.modified = True
    self.s = classSection.NewAnalyser()
    for elem in self.box1.get_children():
      self.box1.remove(elem)
    for elem in self.box2.get_children():
      self.box2.remove(elem)
    for elem in self.box3.get_children():
      self.box3.remove(elem)
    try:
      del(self.p1)
    except AttributeError:
      pass
    self.path = None
    GLib.idle_add(self.area.queue_draw)


  def on_add_node(self, widget):
    self.modified = True
    nodes =  self.s.nodes
    i = 0
    name = "N1"
    while name in nodes:
      i += 1
      name = "N%d" % i
    Obj = NodeWidget(name, self.s)
    hbox = Obj.add_hbox(self)
    self.box1.pack_start(hbox, False, False, 0)
    hbox.show_all()

    combos = get_combos_list1(self)
    for combo in combos:
      combo.append_text(name)

    self.on_draw()


  def on_add_arc(self, widget):
    self.modified = True
    nodes =  self.s.arcs
    i = 0
    name = "Arc1"
    while name in nodes:
      i += 1
      name = "Arc%d" % i
    Obj = ArcWidget(name, self.s)
    hbox = Obj.add_hbox(self)
    self.box2.pack_start(hbox, False, False, 0)
    hbox.show_all()

  def on_add_arc1(self, obj, cat):
    self.modified = True
    hbox = obj.hbox
    Id = obj.id
    for child in hbox.get_children():
      hbox.remove(child)
    arcs = self.s.arcs
    nodes = self.s.nodes
    arcs[Id] = classSection.Arc(Id, cat, nodes)
    Obj = ArcWidget1(Id, cat)
    hbox = Obj.add_hbox(self, hbox)
    hbox.show_all()

  def on_add_path(self, widget):
    self.modified = True
    nodes = self.s.paths
    i = 0
    name = "C1"
    while name in nodes:
      i += 1
      name = "C%d" % i
    Obj = ContourWidget(name)
    self.s.paths[name] = None
    hbox = Obj.add_hbox(self)
    self.box3.pack_start(hbox, False, False, 0)
    hbox.show_all()

  def on_add_poly(self, obj):
    self.modified = True
    hbox = obj.hbox
    Id = obj.id
    for child in hbox.get_children():
      hbox.remove(child)
    path = classSection.Path(Id, [], True, self.s.nodes, self.s.arcs)
    self.s.paths[Id] = path
    Obj = PathWidget(Id)
    hbox = Obj.add_hbox(self, hbox)
    hbox.show_all()

  def on_add_circle(self, obj):
    self.modified = True
    hbox = obj.hbox
    last = hbox.get_children()[-1]
    hbox.remove(last)
    label = Gtk.Label(label="Cercle :")
    label.set_size_request(70, 35)
    hbox.pack_start(label, False, False, 0)
    label.show()
    b= Gtk.MenuButton()
    b.set_size_request(50, 35)
    menu = Gtk.Menu()
    menuitem = Gtk.MenuItem(label="Cercle centre et point")
    menuitem.show()
    menuitem.connect_object("activate", self.on_add_circle1, obj)
    menu.append(menuitem)
    menuitem = Gtk.MenuItem(label="Cercle centre et rayon")
    menuitem.show()
    menuitem.connect_object("activate", self.on_add_circle2, obj)
    menu.append(menuitem)
    b.set_popup(menu)
    b.show_all()
    hbox.pack_start(b, False, False, 0)

  def on_add_circle1(self, obj):
    hbox = obj.hbox
    Id = obj.id
    for child in hbox.get_children():
      hbox.remove(child)
    path = classSection.CirclePathCP(Id, None, None, True, self.s.nodes)
    self.s.paths[Id] = path
    Obj = CircleWidget(Id)
    hbox = Obj.add_hbox(self, hbox)
    hbox.show_all()


  def on_add_circle2(self, obj):
    hbox = obj.hbox
    Id = obj.id
    for child in hbox.get_children():
      hbox.remove(child)
    path = classSection.CirclePathCR(Id, None, None, True, self.s.nodes)
    self.s.paths[Id] = path
    Obj = CircleWidgetCR(Id)
    hbox = Obj.add_hbox(self, hbox)
    hbox.show_all()

  def on_remove_arc(self, widget):
    self.modified = True
    nodes = self.s.arcs
    deleted = []
    for elem in self.box2.get_children():
      if elem.get_children()[0].get_active():
        name = elem.get_children()[1].get_text()
        del(nodes[name])
        deleted.append(name)
        self.box2.remove(elem)
    # suppression éventuelle du noeud des Paths 
    deleted_widgets = []
    for elem in self.box3.get_children():
      for widget in elem.get_children()[3:-3]:
        if widget.get_active_text() in deleted:
          deleted_widgets.append(widget)
        remove_combo_items(widget, deleted)
    for line in self.box3.get_children():
      for child in line.get_children():
        if child in deleted_widgets:
          line.remove(child)
    self.on_draw()


  def on_remove_path(self, widget):
    self.modified = True
    nodes = self.s.nodes
    for elem in self.box3.get_children():
      if elem.get_children()[0].get_active():
        try:
          name = elem.get_children()[2].get_text()
          del(self.s.paths[name])
        except AttributeError:
          pass
        self.box3.remove(elem)
    self.on_draw()

  def on_remove_node(self, widget):
    self.modified = True
    nodes = self.s.nodes
    deleted = []
    for elem in self.box1.get_children():
      if elem.get_children()[0].get_active():
        name = elem.get_children()[2].get_text()
        del(nodes[name])
        deleted.append(name)
        self.box1.remove(elem)
    # suppression du noeud dans les combo des arcs et des paths
    combos = get_combos_list1(self)
    for combo in combos:
      remove_combo_items(combo, deleted)

    # suppression éventuelle du noeud des Paths 
    deleted_widgets = []
    for elem in self.box3.get_children():
      widgets = elem.get_children()
      if elem.get_name() == 'PathWidget':
        for combo in widgets[3:-3]:
          if combo.get_active_text() in deleted:
            deleted_widgets.append(combo)
          remove_combo_items(combo, deleted)
      elif elem.get_name() == 'CircleWidget':
        combo = widgets[4]
        remove_combo_items(combo, deleted)
        combo = widgets[6]
        remove_combo_items(combo, deleted)
      elif elem.get_name() == 'CircleWidgetCR':
        combo = widgets[4]
        remove_combo_items(combo, deleted)
    for line in self.box3.get_children():
      for child in line.get_children():
        if child in deleted_widgets:
          line.remove(child)
    self.on_draw()

  def on_save(self, widget):
    #print("on_save ", self.path)
    self.on_run(None)
    if self.path is None:
      self.path = file_tools.file_save("", ext=".xml")
      if not file_tools.save_as_ok_func(self.path):
        return
    file_name = self.path.split('/')[-1]
    self.s.file = file_name
    try:
      f = open(self.path, 'w')
      string = self.get_xml()
      f.write('<?xml version="1.0" encoding="UTF-8"?>'+string)
      f.close()
      print("Recording successfully completed")
    except:
      print("An error has occurred during recording")
    self.window.set_title("Gestionnaire de sections droites - %s" % file_name)

  def on_export(self, widget):
    """Effectue une sauvegarde de l'écran au format jpg ou svg"""
    data = file_tools.file_export()
    if data is None:
      return
    file1 = data[0]
    format1 = data[1]
    if not file_tools.save_as_ok_func(file1):
      return
    x0 = self.x0
    y0 = self.y0
    w = self.w - 2*self.margin
    h = self.h - 2*self.margin
    if format1 == 'PNG':
      surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.w, self.h)
      cr = cairo.Context(surface)
      cr.set_source_rgb(1, 1, 1)
      cr.rectangle(0, 0, self.w, self.h)
      cr.fill()
      cr.paint()
      self.p1 = self.CairoDraw(cr, x0, y0, w, h)
      self.area.queue_draw()
      for pattern in self.p1:
        cr.set_source(pattern)
        cr.paint()
      cr.paint_with_alpha(1)
      surface.write_to_png(file1)
      surface.finish()
    elif format1 == 'SVG':
      surface = cairo.SVGSurface(file1, self.w, self.h)
      cr = cairo.Context(surface)
      self.p1 = self.CairoDraw(cr, x0, y0, w, h)
      self.area.queue_draw()
      for pattern in self.p1:
        cr.set_source(pattern)
        cr.paint()
      cr.paint_with_alpha(1)
      surface.finish()

  def on_about(self, widget):
    about()



  def GetCairoScale(self, w0, h0):
    self.box = self.s.GetBox()
    #print("box=", self.box)
    if self.box is None: 
      return 1
    xmin, ymin, xmax, ymax = self.box
    w = xmax - xmin
    h = ymax - ymin
    max_s = max(w, h)
    if w == 0: scalex = None
    else: scalex = w0 / w
    if h == 0: scaley = None
    else: scaley = h0 / h
    if scalex is None and scaley is None: return 1
    elif scalex is None: return scaley
    elif scaley is None: return scalex
    return min(scalex, scaley)

  def CairoDraw(self, cr, X0, Y0, w, h):
    nodes = self.s.nodes
    #print("Cairo=",nodes)
    arcs = self.s.arcs
    self.scale = scale = self.GetCairoScale(w, h)
    if self.box is None: return []
    x0, y0, x1, y1 = self.box
    w0, h0= x1-x0, y1-y0
    cr.push_group()
    cr.save()
    cr.stroke()
    cr.set_line_width(2)
    cr.translate(X0-x0*scale, Y0+y0*scale)
    pattern = []
    # ------- Repères ----------
    cr.save()
    cr.set_source_rgb(0, 0, 1)
    cr.move_to(0, 0)
    cr.line_to(50, 0)
    cr.stroke()
    arrow(cr, 50, 0, 6, 0)
    cr.move_to(50, -5)
    cr.show_text('X')

    cr.move_to(0, 0)
    cr.line_to(0, -50)
    cr.stroke()
    arrow(cr, 0, -50, 6, math.pi/2)
    cr.move_to(-10, -50)
    cr.show_text('Y')

    cr.restore()

    # ----- Noeuds -------------
    for node_id in nodes:
      node = nodes[node_id]
      node.draw(cr, scale)
    # ----- Tronçon d'Arc -------------
    cr.save()
    cr.set_line_width(1)
    cr.set_dash([2])
    for a in arcs:
      a = arcs[a]
      a.draw(cr, scale)
    cr.restore()

    # ----- Paths & Circles -------------
    for path_id in self.s.paths:
      path = self.s.paths[path_id]
      if path is None: continue
      path.draw(cr, scale)

    # ---------       CDG
    if not hasattr(self.s, 'section'): 
      cr.restore()
      pattern.append(cr.pop_group())
      return pattern
    xmin, ymin, xmax, ymax = self.box
    w = xmax - xmin
    h = ymax - ymin
    if w == 0 or h == 0: 
      cr.restore()
      pattern.append(cr.pop_group())
      return pattern
    cr.restore()
    obj = self.s.section
    if not self.modified and not obj.XG is None:
      cr.save()
      cr.translate(X0+(-x0+obj.XG)*scale, Y0+(y0-obj.YG)*scale)
      cr.set_font_size(14)
      angle = self.s.section.a_xu
      self.draw_repere(cr, obj, scale, 0)
      self.draw_repere(cr, obj, scale, angle)
      cr.arc(0, 0, 4, 0, 6.29)
      cr.fill()
      cr.move_to(15, -15)
      cr.show_text("G")

      #print(cr.user_to_device(0, 0))
      cr.restore()
    pattern.append(cr.pop_group())
    return pattern

  def draw_repere(self, cr, obj, scale, angle):
    """Dessine les repères passants par G en fonction de l'angle fourni"""
    x0, y0, x1, y1 = self.box
    w0, h0= x1-x0, y1-y0
    cr.save()
    #cr.set_line_width(1)
    cr.set_dash([3])
    texts = ['x', 'y']
    if not angle < 1e-4:
      texts = ['u', 'v']
      cr.rotate(-angle)
      cr.set_source_rgb(0, 1, 0)
    else:
      cr.set_source_rgb(1, 0, 0)
    cr.move_to(0, -obj.vsup*scale-30)
    cr.rel_line_to(0, (obj.vsup+obj.vinf)*scale+60)
    cr.stroke()
    cr.move_to(-20+(x0-obj.XG)*scale, 0)
    cr.rel_line_to(w0*scale + 40, 0)
    cr.stroke()
    cr.move_to((w0+x0-obj.XG)*scale+10, -15)
    cr.show_text(texts[0])
    cr.move_to(5, -obj.vsup*scale-30)
    cr.show_text(texts[1])
    cr.restore()

  def draw_surface_bg(self, cr):
    """Draw white background on drawingare"""
    cr.rectangle(0, 0, self.w, self.h)
    cr.fill()

  def on_expose(self, widget, cr):
    """Méthode expose-event pour le drawingarea du lancement"""
    cr.set_source_surface(self.surface, 0, 0)
    if hasattr(self, "p1"):
      for pattern in self.p1:
        cr.set_source(pattern)
        cr.paint()

  def configure_first_page(self, widget, event):
    self.w = w_alloc = widget.get_allocated_width()
    self.h = h_alloc = widget.get_allocated_height()
    self.x0 = self.margin
    self.y0 = self.h - self.margin
    self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, w_alloc, h_alloc)
    GLib.idle_add(self.update_drawing)

  def on_destroy_main(self, widget, event=None):
    Gtk.main_quit()

  def on_destroy(self, widget, event=None):
    self.window = None
    return False



if __name__=='__main__':
  print ("Not implemented")
