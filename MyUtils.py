#----------------------------------------------------------------------
# Copyright (c) 2013, Guy Carver
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#
#     * The name of Guy Carver may not be used to endorse or promote products # derived#
#       from # this software without specific prior written permission.#
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# FILE    MyUtils.py
# BY      Guy Carver
# DATE    06/12/2013 09:26 PM
#----------------------------------------------------------------------

import sublime, sublime_plugin
from xml.dom.minidom import parse, parseString
import os, stat, datetime, re
# from Edit.edit import Edit

sets_file = "MyUtils.sublime-settings"
mu_settings = None

def plugin_loaded(  ) :
  global mu_settings
  mu_settings = sublime.load_settings(sets_file)

def CheckTag( aNode, aTag ) :
  return ((len(aNode.childNodes) == 1) and (aNode.childNodes[0].data == aTag))

def FindValueTag( aElems, aTag ) :
  for e in aElems :
    strs = e.getElementsByTagName("string")
    if len(strs) == 2 :
      if CheckTag(strs[0], aTag) :
        return(strs[1])

  return None

class SetClassNameCommand( sublime_plugin.TextCommand ) :
  def SetIt( self, aName ) :
    # shell_vars = self.view.meta_info("shellVariables", aPoint)
    # print(shell_vars)
    # if shell_vars :
    #   for v in shell_vars :
    #     if v["name"] == "TM_CLASS" :
    #       v["value"] = aName
    fileName = os.path.join(sublime.packages_path(), "C++/Class (C++).tmPreferences")
    prefs = parse(fileName)  # parse an XML file by name
    dicts = prefs.getElementsByTagName("dict")
    vt = FindValueTag(dicts, "TM_CLASS")
    if vt :
      print("found entry and setting to " + str(aName))
      print(vt.childNodes)
      if len(vt.childNodes) > 0 :
        vt.childNodes[0].data = aName
      else:
        ne = prefs.createTextNode(aName)
        vt.appendChild(ne);

      file = open(fileName, "w")
      prefs.writexml(file)
      file.close()

  def run( self, edit ) :
    vw = self.view
    sel = vw.sel()[0]
    word = vw.word(sel)
    className = vw.substr(word)
    self.SetIt(className)

class ShowScopeCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    print("Showing Scope.\n")
    sels = self.view.sel()
    name = self.view.scope_name(sels[0].begin())
    print("Scope: " + name)

class GetClassNameCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view

    vw.run_command("insert_snippet", {"contents": "$TM_CLASS::"})
    # name = ClassName + "::"
    # for sel in vw.sel() :
    #   point = sel.end()
    #   vw.insert(edit_init, point, name)

def GetClassName( vw, aPoint ) :
  sv = vw.meta_info("shellVariables", aPoint)
  for v in sv :
    if v["name"] == "TM_CLASS" :
      return v["value"]
  return ""

def FindMyRegion( vw, aName, aRegion ) :
  params = vw.find_by_selector(aName)
  for r in params :
    if r.intersects(aRegion) :
      return r
  return None

def FindParamNames( vw, curline ) :
  linestr = vw.substr(curline)
#   print("Searching on " + linestr)
  funcNameRegion = FindMyRegion(vw, "meta.function.c", curline)
  if funcNameRegion :
    rValueRegion = sublime.Region(curline.a, funcNameRegion.a)
    rvalueStr = vw.substr(rValueRegion)
#    print(vw.substr(funcNameRegion))
    rvalue = rvalueStr.split(" ")[-1]
#    print("return: " + rvalue)
    params = FindMyRegion(vw, "meta.parens.c", curline)
    if params :
      paramString = vw.substr(params)
      paramList = paramString.split(",")
      rfparamList = [ r.strip("( ,)\r\n\t") for r in paramList ]
#      print(rfparamList)
      if len(rfparamList) :
        def getname(astr) :
          sp = astr.split(" ")
          return "" if len(sp) <= 1 else sp[1].strip(" *&")
        paramNames = [ getname(p) for p in rfparamList if len(p)]
      else:
        paramNames = None
#      print(funcNameRegion)
#      print(rvalue)
#      print(paramNames)
#      print(params)
      return (funcNameRegion, rvalue, paramNames, params)
  return (None, None, None, None)

#funexp = re.compile("(virtual |)(.+ )((.+)::)?(.+)\((.*?)[ &*]?(.*\))( const)?( override|;)?")
funexp = re.compile("[ \t]*(virtual |)(.+ )((.+)::)?(.+)\( ?(.*)\)( const)?( override|;)?")
paramexp = re.compile("(const |)(\w+?)[*& ]+(\w*)[, )]+(.*)")

def GetParams( ParamString ) :
  ps = ParamString
  pa = []
  while len(ps) :
    p = paramexp.match(ps)
    if (p != None) :
      pa.append(p.group(3))
      ps = p.group(4)
    else:
      break
  return pa

class MakeFunctionCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view

    for sel in vw.sel():
      selLine = vw.line(sel.begin())
#      FindParamNames(vw, selLine)

      match = funexp.search(vw.substr(selLine))
      if match != None :
#        print("fungroups: {}".format(match.groups()))
        grps = match.groups()
        comline = "///\n/// <summary> "
        if (grps[0]):
          comline += grps[0].rstrip().upper() + ":"
        comline += " </summary>\n"
        if (grps[5]):
          #Add parameters.
          pa = GetParams(grps[5])
          for p in pa :
            comline += "/// <param name=\"" + p + "\">  </param>\n"
        if (grps[1] and not grps[1] == "void ") :
          comline += "/// <returns> " + grps[1] + "</returns>\n"
        comline += '///\n'

        newline = ""
        newline += grps[1] if grps[1] else "void "
        if (grps[3]):
          newline += grps[2]
        else:
          cname = GetClassName(vw, sel.begin())
          if (cname):
            newline += cname + "::"
        newline += grps[4] + "( "
        if (grps[5]):
          newline += grps[5]
        newline += " )"
        if (grps[6]):
          newline += grps[6]
        newline += "\n{\n\t//Code\n}\n"
#        print(newline)
        vw.replace(edit, selLine, comline + newline)

class OpenSelectedFilesCommand( sublime_plugin.TextCommand ) :
### read lines from a view and assume each line is a file name
###  Attempt to load the files and print an error if not found.
  def run( self, edit ) :
    vw = self.view
    w = vw.window()

    rset = vw.sel()
    for r in vw.sel() :
      lines = vw.lines(r)
      for l in lines :
        fname = vw.substr(l).strip()
#        print("opening " + fname)
        if os.access(fname, os.R_OK) :
          try:
            w.open_file(fname)
          except:
            print("Failed to open " + fname)
        else:
          print("Failed to open " + fname)

class InsertAccentCharCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    accents = ['ñ', 'á', 'é', 'í', 'ó', 'ú']

    def select( aIndex ) :
      if aIndex != -1 :
        vw = self.view
        accent = accents[aIndex]
        for s in vw.sel() :
          vw.insert(edit, s.a, accent)

    self.view.show_popup_menu(accents, select)

class MyTestCommand( sublime_plugin.WindowCommand ) :
  def run( self ) :
    for s in self.window.settings() :
      print(s)

class OpenMyFileCommand( sublime_plugin.WindowCommand ) :
  def run( self, file ) :
    self.window.open_file(file)

class RepitCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view

    lines = vw.sel()
    for s in lines :
      rc1 = vw.rowcol(s.a)
      rc2 = vw.rowcol(s.b)
      if (rc1[0] != rc2[0]) :
        a = s.a
        if (rc1[0] > rc2[0]) :
          rc1, rc2 = rc2, rc1
          a = s.b
        pnt = vw.text_point(rc1[0], rc2[1])
        r = sublime.Region(a, pnt)
        str = vw.substr(r)
        for i in range(rc1[0] + 1, rc2[0] + 1) :
          pnt = vw.text_point(i, rc1[1])
          # Make sure there is room on the line for the insert.
          ln = vw.line(vw.text_point(i, 0))
          if ln.b >= pnt :
            vw.insert(edit, pnt, str)
      else:
        #If no selection and not at the 1st row we will duplicate the character from the line above.
        if (rc1[1] == rc2[1]) and (rc1[0] > 0) :
          pnt = vw.text_point(rc1[0] - 1, rc1[1])
          r = sublime.Region(pnt, pnt + 1)
          str = vw.substr(r)
          vw.insert(edit, s.a, str)

def NewRegion( aView, aR1, aR2 ) :
  """Create a region to encompass all of the lines between the 2
     given regions"""
  (r1Line, _) = aView.rowcol(aR1.a)
  (r2Line, _) = aView.rowcol(aR2.a)
  tp2 = aView.text_point(r2Line, 0) - 1
  return(sublime.Region(aView.text_point(r1Line + 1, 0), tp2));

class ShowRoutinesCommand( sublime_plugin.TextCommand ) :
  def run( self, edit) :
    vw = self.view
#   The following line finds c/c++ function names.
#    regions = vw.find_all("""^[a-zA-Z0-9_].*\)[ \t]*\{?[ \t]*\}?$""")
    regions = vw.find_by_selector("entity")
    last = len(regions)

    if last :
      beginRegion = sublime.Region(0, 0)
      #create a region to start at the beginning of the file.
      if regions[0].begin() > 1 :
        folds = [ NewRegion(vw, beginRegion, regions[0]) ]
      else:
        folds = []

      folds = folds + [ NewRegion(vw, regions[i - 1], regions[i])
        for i in range(1, last) ]

      #Now add a region to encompass up to the end of the file.
      endRegion = sublime.Region(vw.size(), vw.size())
      folds.append(NewRegion(vw, regions[last - 1], endRegion))

      vw.fold(folds)
      #Focus on 1st function and set caret to it as well.
      vw.show_at_center(folds[0])
      (line, _) = vw.rowcol(folds[0].a)
      vw.run_command("goto_line", {"line": line})

class PickOpenFilesCommand( sublime_plugin.WindowCommand ) :
  def run( self ) :
    win = self.window
    views = win.views()
    if views and len(views) :
      vnames = [ v.file_name() if v.file_name() else v.name() for v in views ]
      win.show_quick_panel(vnames, self.select)

  def select( self, aIndex ) :
    if aIndex != -1 :
      self.window.focus_view(self.window.views()[aIndex])

class MoveToTopCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    vr = vw.visible_region()
    s = vw.sel()[0]
    (tl, _) = vw.rowcol(vr.a)
    (bl, _) = vw.rowcol(vr.b)
    lines = (bl - tl) / 2
    (curL, _) = vw.rowcol(s.a)
    lines += curL
    pnt = vw.text_point(lines, 0)
    vw.show_at_center(pnt)

class SemicolonEndCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    for s in vw.sel() :
      line = vw.line(s)
      e = vw.substr(line.b - 1)
      if e == ';' :
        er = sublime.Region(line.b - 1, line.b)
        vw.erase(edit, er)
      else:
        vw.insert(edit, line.b, ";")

class DateTimeCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    t = datetime.datetime.now()
    tstr = t.strftime("%m/%d/%Y %I:%M %p")

    for s in vw.sel() :
      if (s.empty()):
        vw.insert(edit, s.begin(), tstr)
      else:
        vw.replace(edit, s, tstr)

class ParenEndCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    for s in vw.sel() :
      line = vw.line(s)
      ls = vw.substr(line)
      ip = -1
      c = ls[ip]
      if (c == ";") :
        ns = ls[:ip] + ")" + ls[ip:]
      else:
        ns = ls + ")"

      vw.replace(edit, line, ns)

def GetTabSize( view ) :
  return int(view.settings().get('tab_size', 4))

def LineWidth( aComment, aTabSize, aLine ) :
  '''Convert \t (tabs) into spaces for string length counting.
     return char pos and column'''
  ln = 0
  cs = 0
  for ch in aLine :
    cs += 1
    if ch == '\t' :
      ln += aTabSize
      ln -= ln % aTabSize
    else:
      ln += 1

  return cs, ln

def FromPointToTarget( aTabSize, aLine, aPoint, aTarget ) :
  pos = aPoint

  while aTarget > 0:
    c = aLine[pos]
    pos -= 1
    aTarget -= aTabSize if (c == '\t') else 1

  return pos - aPoint

def GetComment( aView ) :
  point = aView.sel()[0].a
  shell_vars = aView.meta_info("shellVariables", point)
  if shell_vars :
    for v in shell_vars :
      if v["name"] == "TM_COMMENT_START" :
        return v["value"]

  return ""

def GetCommentColumn( aView ) :
  return int(aView.settings().get('comment_column', 49))

class MyToggleCommentCommand( sublime_plugin.TextCommand ) :

  def run( self, edit ) :
    vw = self.view
    cmnt = GetComment(vw)
    for s in vw.sel() :
      lines = vw.lines(s)

      lineText = vw.substr(lines[0]);

      if lineText.startswith(cmnt) :
        for line in lines[::-1] :
          lineText = vw.substr(line)
          if lineText.startswith(cmnt) :
            remR = sublime.Region(line.begin(), line.begin() + len(cmnt))
            vw.replace(edit, remR, "")
      else:
        for line in lines[::-1] :
          lineText = vw.substr(line)
          vw.insert(edit, line.begin(), cmnt)

class CommentEolCommand( sublime_plugin.TextCommand ) :

  def run( self, edit ) :
    vw = self.view
    column = GetCommentColumn(vw)
    spcs = GetTabSize(vw)
    cmnt = GetComment(vw)

    for s in vw.sel() :
      lines = vw.lines(s)
      #iterate over the lines backwards or the comment additions
      # will not be placed in the correct place as the values in the
      # lines are not updated with the new characters.
      for line in lines[::-1] :
        lineText = vw.substr(line)
        rcomment = lineText.rfind(cmnt)

        #if no comment currently on the line then add one.
        if rcomment == -1 :
          cs, c = LineWidth(cmnt, spcs, lineText)
          c -= c % spcs                         # Round down for correct tab count.
          target = column - c
#           print("{} - {} = {}".format(column, c, target))
          #Find the end of line and calculate destination column.
          count = 1 if target <= 0 else target // spcs
#           print("{} / {} = {}".format(target, spcs, count))

          #Insert number of tabs needed to reach target.
          strng = "\t" * int(count) + cmnt
          vw.insert(edit, line.b, strng)
        else:
          #Comment exists, move it to the desired spot.
          cmntCountStr = lineText[:rcomment]
          #get line pnt, column of comment
          cs, c = LineWidth(cmnt, spcs, cmntCountStr)
#           print("{} width {}".format(cmntCountStr, c))
          target = column - c
          if target < 0 :
#             print("< {}, {}, {}".format(column, c, target))
            target = FromPointToTarget(spcs, lineText, cs - 1, 1 - target)
#             print("Removing " + str(target))
            cmntPnt = line.a + cs
            remR = sublime.Region(cmntPnt + target, cmntPnt)
            vw.replace(edit, remR, "")
          elif target > 0 :
#             print("> {}, {}, {}".format(column, c, target))
            count = target // spcs
#             print("spces {}, cnt {}".format(spcs, count))

            #Insert number of tabs needed to reach target.
            strng = "\t" * count
            vw.insert(edit, line.a + rcomment, strng)

      # Now that we are done move to the 1st comment in 1st line of the selection.
      line = vw.line(vw.sel()[0].begin())
      lineText = vw.substr(line)
      rcomment = lineText.rfind(cmnt)
      p = line.begin() + rcomment + len(cmnt)
#       print("{}, {}, {}".format(rcomment, p, lineText))

      #add comment tag and move the cursor to the end of the line.
      vw.sel().clear()
      vw.sel().add(sublime.Region(p, p))

class ShowFileNameCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    self.view.set_status("fname", self.view.name() if self.view.name() else self.view.file_name())
    sublime.set_timeout(self.TurnOff, 20000)

  def TurnOff( self ) :
    self.view.erase_status("fname")

class MyPickFileCommand( sublime_plugin.WindowCommand ) :
  '''Show list of files to pick from'''

  def run( self ) :
    #get list from settngs.
    items = mu_settings.get("slots", [""])
    #function to call on selection.
    def done( index ) :
      if index >= 0 :
        self.window.open_file(items[index])

    #open a selection prompt
    self.window.show_quick_panel(items, done)

class ShowProjectNameCommand( sublime_plugin.WindowCommand ) :
  def run( self ) :
    self.window.active_view().set_status("pname", self.window.project_file_name())
    sublime.set_timeout(self.TurnOff, 20000)

  def TurnOff( self ) :
    self.window.active_view().erase_status("pname")

# { "keys": ["shift+f5"], "command": "my_search" },
# class MySearchCommand( sublime_plugin.TextCommand ) :
#   def run( self, edit ) :
#     vw = self.view
#     wn = vw.window()
#     wordr = vw.word(vw.sel()[0].a)
#     word = vw.substr(wordr)

#     wn.run_command("show_panel", {"panel": "incremental_find", "reverse": False})
#     srchvw = wn.get_output_panel("incremental_find")
#     srchvw.insert(myedit, 0, word)
#     srchvw.end_edit(myedit)

class Set8thSyntax( sublime_plugin.WindowCommand ):
  def run( self ):
    self.window.active_view().set_syntax_file("Packages/8th/8th.sublime-syntax")

class AutoSemiColonCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        # Loop through and add the semi colon
        for sel in self.view.sel():
            # The last letter we've dealt with
            first = sel.end()
            self.view.insert(edit, first, ';')

        # Loop through and add move it to the end
        for sel in self.view.sel():
            last = last_bracket = first = sel.end()
            # Find the last bracket
            while (self.view.substr(last) in [' ', ')', ']']):
                if (self.view.substr(last) != ' '):
                    last_bracket = last + 1
                last += 1

            if (last_bracket < last):
                last = last_bracket

            # Can we insert the semi colon elsewhere?
            if last > first:
                self.view.erase(edit, sublime.Region(first - 1, first))
                # Delete the old semi colon
                self.view.insert(edit, last - 1, ';')
                # Move the cursor
                self.view.sel().clear()
                self.view.sel().add(sublime.Region(last, last))

class DateCommand(sublime_plugin.TextCommand):
  """Prints Date"""
  def run(self, edit):
    self.view.insert(
      edit,
      self.view.sel()[0].begin(),
      datetime.now().strftime("%d/%m/%Y")
      )

class HourCommand(sublime_plugin.TextCommand):
  """Prints only H:M"""
  def run(self, edit):
    self.view.insert(
      edit,
      self.view.sel()[0].begin(),
      datetime.now().strftime("%H:%M")
      )

def SetReadOnly( vw, m ) :
  ro = ((m & stat.S_IWRITE) == 0)
  vw.set_read_only(ro)
  if (ro) :
    vw.set_status("RO", "ReadOnly")
  else:
    vw.erase_status("RO")

class ToggleReadOnlyCommand( sublime_plugin.TextCommand ) :
  ### Toggle the readonly state of the file and set the view readonly state to match.
  def run( self, edit, update = False ) :
    vw = self.view
    fn = vw.file_name()
    if fn :
      try:
        st = os.stat(fn)
        m = st.st_mode
        #if not just updating the view status then change the file status.
        if not update :
          m = m ^ stat.S_IWRITE
          os.chmod(fn, m)
        SetReadOnly(vw, m)
      except Exception as ex:
        print(ex)

class ReadOnlyUpdater( sublime_plugin.EventListener ) :
  def on_load_async( self, view ) :
    fn = view.file_name()
    if fn :
      try:
        SetReadOnly(view, os.stat(fn).st_mode)
      except:
        pass

class SwapWordsCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    r = vw.sel()[0]

    #Get either word under cursor or selection
    if r.size() == 0 :
      r = vw.word(r.begin())

    pm = vw.get_regions("swap")

    # If no mark
    if len(pm) == 0:
      vw.add_regions("swap", [r], "yellow")
      return  #return without erasing regions.
    else:
      r1 = pm[0]
      #Don't swap if regions intersect.
      if not r1.intersects(r) :

        #Sort marks by order in file.
        if r.begin() < r1.begin() :
          rr = (r1, r)
        else:
          rr = (r, r1)

        #Copy text of both marks.
        t0 = vw.substr(rr[0])
        t1 = vw.substr(rr[1])

        #Replace last mark 1st.
        vw.replace(edit, rr[0], t1)
        #Replace other mark.
        vw.replace(edit, rr[1], t0)

    vw.erase_regions("swap")

class CopyandCommentCommand( sublime_plugin.TextCommand ) :
  """ Copy a line and toggle comment on the original """
  def run( self, edit ) :
    vw = self.view
    line = vw.full_line(vw.sel()[0].begin())
    cstr = vw.substr(line)
    #Comment out the original line.
    vw.run_command("toggle_comment",  {"block": False})
    r, c = vw.rowcol(line.begin())
    r += 1
    pnt = vw.text_point(r, 0)
    #Make a copy of the line.
    vw.insert(edit, pnt, cstr)
    vw.sel().clear()
    vw.sel().add(sublime.Region(pnt))    #Move cursor to line.
    vw.show(pt)

#The following indent functions are copied from block.py
#  A change to indented_block() to fix a bug with indentation checking
#  was made and this needs to be here until that is officially fixed.

def next_line(view, pt):
    return view.line(pt).b + 1

def prev_line(view, pt):
    return view.line(pt).a - 1

def is_ws(str):
    for ch in str:
        if ch != ' ' and ch != '\t':
            return False
    return True

class BlockLinesCommand(sublime_plugin.TextCommand) :
  '''Add { } around and indent all selected lines.'''
  def run(self, edit, indented = False ) :
    vw = self.view
    sels = vw.sel()
    ts = GetTabSize(vw)   #Get tab size.
    cmnt = GetComment(vw) #Get comment text.
    for s in sels :
      if (indented):      #If we want the indented region select it.
        s = vw.indented_region(s.a)

      c = vw.indentation_level(s.a)
      #{} go 1 indentation level less.
      if indented :
        c = max(0, c - 1)
      ls = vw.lines(s)
      fl = vw.full_line(ls[-1])
      indtext = '\t' * c
      vw.insert(edit, fl.end(), indtext + "}\n")
      #if not already indented then insert a tab to indent all lines.
      if not indented:
        for l in ls[::-1] : #Process lines backwards.
          st = vw.substr(l)
          if not (st.startswith(cmnt) or st.startswith('#')) :
            vw.replace(edit, l, "\t" + st)

      #if indenting a whole indentation block sel is at beginning of line
      # so add tabs fst.  Otherwise the cursor is at the tab position so
      # add them last so they are applied to the next line.
#      if indented :
      begtext = indtext + "{\n"
#      else:
#        begtext = "{\n" + indtext

      fl = vw.full_line(s)
      vw.insert(edit, fl.a, begtext)

class TestIndentCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    r = vw.sel()[0]
    if r.empty():
      nl = next_line(vw, r.a)
      nr = vw.indented_region(nl)
      ss = vw.substr(nr)
      print("nr =\n" + ss)
      if nr.a < nl:
        nr.a = nl

      this_indent = vw.indentation_level(r.a)
      next_indent = vw.indentation_level(nl)

      ok = False

      if this_indent + 1 == next_indent:
        ok = True

      if not ok:
        prev_indent = vw.indentation_level(prev_line(vw, r.a))

        # Mostly handle the case where the user has just pressed enter, and the
        # auto indent will update the indentation to something that will trigger
        # the block behavior when { is pressed
        line_str = vw.substr(vw.line(r.a))
        if is_ws(line_str) and len(vw.get_regions("autows")) > 0:
          if prev_indent + 1 == this_indent and this_indent == next_indent:
              ok = True

      if ok:
        # ensure that every line of nr is indented more than nl
        l = next_line(vw, nr)
        while l < nr.end():
          line_str = vw.substr(vw.line(r.a))
          print("ln = " + line_str)
          if vw.indentation_level(l) == next_indent:
            print("Not all lines indented.")
            return False
          l = next_line(vw, l)
        print("Ok")
        return True
      else:
        print("Not ok.")
        return False

    print("Sel Not Empty.")
    return False

def indented_block(view, r):
  if r.empty():
    nl = next_line(view, r.a)
    nr = view.indented_region(nl)
    if nr.a < nl:
        nr.a = nl

    this_indent = view.indentation_level(r.a)
    next_indent = view.indentation_level(nl)

    ok = False

    if this_indent + 1 == next_indent:
      ok = True

    if not ok:
      prev_indent = view.indentation_level(prev_line(view, r.a))

      # Mostly handle the care where the user has just pressed enter, and the
      # auto indent will update the indentation to something that will trigger
      # the block behavior when { is pressed
      line_str = view.substr(view.line(r.a))
      if is_ws(line_str) and len(view.get_regions("autows")) > 0:
        if prev_indent + 1 == this_indent and this_indent == next_indent:
          ok = True

    if ok:
      # ensure that every line of nr is indented more than nl
      l = next_line(view, nr)
      while l < nr.end():
        if view.indentation_level(l) == next_indent:
          return False
        l = next_line(view, l)
      return True

  return False

class PrintFileCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    fname = vw.file_name()
    if fname:
      ex = '"%ProgramFiles%/Windows NT/Accessories/WORDPAD.EXE" /p "' + fname + '"'
#      print(ex)
      vw.window().run_command("exec", {"shell_cmd": ex})

class ViewsCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vs = self.view.window().views()
    for v in vs :
      print(v.file_name())

class MyBlockContext(sublime_plugin.EventListener):
  def on_query_context(self, view, key, operator, operand, match_all):
    if key == "myindented_block":
      is_all = True
      is_any = False

      if operator != sublime.OP_EQUAL and operator != sublime.OP_NOT_EQUAL:
        return False

      for r in view.sel():
        if operator == sublime.OP_EQUAL:
          b = (operand == indented_block(view, r))
        else:
          b = (operand != indented_block(view, r))

        if b:
          is_any = True
        else:
          is_all = False

      if match_all:
        return is_all
      else:
        return is_any

    return None


