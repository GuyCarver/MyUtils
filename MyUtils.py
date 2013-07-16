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
import os, stat
from Edit.edit import Edit

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
#      print("found entry and setting to " + str(aClass))
      vt.childNodes[0].data = aName
      file = open(fileName, "w")
      prefs.writexml(file)
      file.close()

  def run( self, edit ) :
    vw = self.view
    sel = vw.sel()[0]
    word = vw.word(sel)
    className = vw.substr(word)
    self.SetIt(className)

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
    rvalue = rvalueStr.split(" ")[-1]
#     print("return: " + rvalue)
    params = FindMyRegion(vw, "meta.parens.c", curline)
    if params :
      paramString = vw.substr(params)
      paramList = paramString.split(",")
      rfparamList = [ r.strip("( ,)\r\n\t") for r in paramList ]
      print(rfparamList)
      if len(rfparamList) :
        paramNames = [ p.split(" ")[1].strip(" *&") for p in rfparamList if len(p)]
      else:
        paramNames = None
      return (funcNameRegion, rvalue, paramNames, params)
  return (None, None, None, None)

class MakeFunctionCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view

    for sel in vw.sel():
      selLine = vw.line(sel.begin())

      funcNameRegion, rvalue, paramNames, paramRegion = FindParamNames(vw, selLine)

      if funcNameRegion :
        if vw.substr(paramRegion.end()) == ';' :
          vw.erase(edit, sublime.Region(paramRegion.end(), paramRegion.end() + 1))

        #todo: Search downward until we find an empty line.  Everything between that and our current
        # position is function body.
        vw.insert(edit, paramRegion.b, "\n{\n\t\n}")

        curLine, _ = vw.rowcol(sel.begin())
        cname = GetClassName(vw, sel.begin())

        vw.insert(edit, funcNameRegion.a + 1, cname + '::')

        newline = lambda x  : (vw.line(vw.text_point(curLine + x, 0)), curLine + x)

        curLineSel, curLine = newline((0, -1)[curLine > 0])

        if curLineSel.begin() == curLineSel.end() :
          vw.insert(edit, curLineSel.begin(), "\n")
          curLineSel, curLine = newline(1)

        #todo: Search upward until we find an empty line.  Everything between that and the function line is summary.

        vw.insert(edit, curLineSel.begin(), "//\n// <summary> ")
        curLineSel, curLine = newline(1)
        pstring = " </summary>"
        if paramNames and (len(paramNames) > 0):
          for p in paramNames :
            pstring += "\n// <param name=" + p + ">  </param>"
        if rvalue and (rvalue != "void") :
          pstring += "\n// <returns> " + rvalue + " </returns>"
        pstring += "\n//"

        vw.insert(edit, curLineSel.end(), pstring)

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


class MyTestCommand( sublime_plugin.WindowCommand ) :
  def run( self ) :
    for s in self.window.settings() :
      print(s)

class OpenMyFileCommand( sublime_plugin.WindowCommand ) :
  def run( self, file ) :
    self.window.open_file(file)

# class RepitCommand( sublime_plugin.TextCommand ) :
#   def run( self, edit ) :
#     vw = self.view

#     lines = vw.sel()
#     numLines = len(lines)
#     if numLines > 1 :
#       reptext = vw.substr(lines[0])
#       for i in range(1, numLines) :
#         vw.insert(edit, lines[i].begin(), reptext)


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
      folds = [ NewRegion(vw, beginRegion, regions[0]) ]
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

def GetTabSize( view ) :
  return int(view.settings().get('tab_size', 4))

def LineWidth( aTabSize, aLine ) :
  len = 0
  for ch in aLine :
    if ch == '\t' :
      len += aTabSize - (len % aTabSize)
    else:
      len += 1

  return len

def CountFromRight( aTabSize, aLine, aCount ) :
  len = 0

  for s in aLine[::-1] :
    if aCount > 0 :
      break;

    # If we ran into something we can't remove try to add a space or tab back
    #  in and exit.  We can't remove as much as we want.
    if (s != '\t' and s != ' ') :
      if len > 0 :
        len -= 1
      break;

    aCount += (aTabSize if s == '\t' else 1)
    len += 1

  return len

class CommentEolCommand( sublime_plugin.TextCommand ) :
  def GetComment( self, aPoint ) :
    shell_vars = self.view.meta_info("shellVariables", aPoint)
    if shell_vars :
      for v in shell_vars :
        if v["name"] == "TM_COMMENT_START" :
          value = v["value"]
          if value :
            return value.strip()

    return ""

  def run( self, edit, column = 57 ) :
    vw = self.view
    spcs = vw.settings().get("tab_size", 2)

    cmnt = self.GetComment(vw.sel()[0].a)
    tab_size = GetTabSize(vw)
    fst = True
    fstColumn = 0

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
          # c = LineWidth(vw, line, tab_size)
          c = LineWidth(tab_size, lineText)
          target = column - c
          # print("{} - {} = {}").format(column, c, target))

          #Find the end of line and calculate destination column.
          if target <= 0 :
            count = 1
            # print("1 tab")
          else:
            #Round up then sub 1 cuz target is 0 based.
            count = (target + spcs - 2) / spcs
            # print("{} / {} = {}".format(target, spcs, count))

          #Insert number of tabs needed to reach target.
          strng = "\t" * int(count) + cmnt
          vw.insert(edit, line.b, strng)
          if fst :
            fstColumn = vw.line(s).b
            fst = False
        else:
          #Comment exists, move it to the desired spot.
          cmntCountStr = lineText[:rcomment]
          c = LineWidth(tab_size, cmntCountStr)
          # print("{} width {}").format(cmntCountStr, c))
          target = column - c
          if target < 0 :
            # print("< " + str(target))
            #Figure out how many characters to remove.
            #Loop backwards through the cmntCountStr until
            removeChars = CountFromRight(tab_size, cmntCountStr, target)
            # print("Removing " + str(removeChars))
            cmntPnt = line.a + rcomment
            count = -removeChars
            remR = sublime.Region(cmntPnt - removeChars, cmntPnt)
            vw.replace(edit, remR, "")
          elif target > 0 :
            # print("> " + str(target))
            count = (target - 1) / spcs

            #Insert number of tabs needed to reach target.
            strng = "\t" * int(count)
            vw.insert(edit, line.a + rcomment, strng)
          if fst :
            # Place the cursor at the end of the comment tag on the 1st line.
            # Have to take into account how many chars were added to the current
            # comment position as well as the length of the comment tag.
            fstColumn = vw.line(s).a + rcomment + count + len(cmnt)
            fst = False

      #add // and move the cursor to the end of the line.
      vw.sel().clear()
      vw.sel().add(sublime.Region(fstColumn, fstColumn))

class ShowFileNameCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    self.view.set_status("fname", self.view.name() if self.view.name() else self.view.file_name())
    sublime.set_timeout(self.TurnOff, 10000)

  def TurnOff( self ) :
    self.view.erase_status("fname")

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

        with Edit(vw) as edit:
          #Replace last mark 1st.
          edit.replace(rr[0], t1)
          #Replace other mark.
          edit.replace(rr[1], t0)

    vw.erase_regions("swap")
