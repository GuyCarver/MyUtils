import sublime, sublime_plugin
from xml.dom.minidom import parse, parseString
import os

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
  def SetIt( self, aPoint, aName ) :
    # shell_vars = self.view.meta_info("shellVariables", aPoint)
    # print shell_vars
    # if shell_vars :
    #   for v in shell_vars :
    #     if v["name"] == "TM_CLASS" :
    #       v["value"] = aName
    fileName = os.path.join(sublime.packages_path(), "C++/Class (C++).tmPreferences")
    prefs = parse(fileName)  # parse an XML file by name
    dicts = prefs.getElementsByTagName("dict")
    vt = FindValueTag(dicts, "TM_CLASS")
    if vt :
#      print "found entry and setting to %s" % aClass
      vt.childNodes[0].data = aName
      file = open(fileName, "w")
      prefs.writexml(file)
      file.close()

  def run( self, edit ) :
    vw = self.view
    sel = vw.sel()[0]
    word = vw.word(sel)
    className = vw.substr(word)
    self.SetIt(word.a, className)

class GetClassNameCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view

    edit_init = vw.begin_edit('ClassName')
    vw.run_command("insert_snippet", {"contents": "$TM_CLASS::"})
    # name = ClassName + "::"
    # for sel in vw.sel() :
    #   point = sel.end()
    #   vw.insert(edit_init, point, name)
    vw.end_edit(edit_init)

class MakeFunctionCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view

    edit_init = vw.begin_edit('make_function')

    vw.run_command("insert_snippet", {"contents": "$TM_CLASS::"})
    # for sel in vw.sel():
    #   first = sel.end()
    #   vw.insert(edit_init, first, ClassName + '::')

    for sel in vw.sel():
      last = vw.line(sel.begin()).end()

      if vw.substr(last - 1) == ';' :
        vw.erase(edit_init, sublime.Region(last - 1, last))

      curLine, _ = vw.rowcol(sel.begin())

      newline = lambda x  : (vw.line(vw.text_point(curLine + x, 0)), curLine + x)

      curLineSel, curLine = newline((0, -1)[curLine > 0])

      if curLineSel.begin() == curLineSel.end() :
        vw.insert(edit, curLineSel.begin(), "\n")
        curLineSel, curLine = newline(1)

      vw.insert(edit, curLineSel.begin(), "//\n//<summary> ")
      curLineSel, curLine = newline(1)
      vw.insert(edit, curLineSel.end(), " </summary>\n//")
      curLineSel, curLine = newline(3)

      if curLineSel.begin() == curLineSel.end() :
        vw.insert(edit, curLineSel.begin(), "\n")

      vw.insert(edit, curLineSel.begin(), "{\n\t")
      curLineSel, curLine = newline(1)
      vw.insert(edit, curLineSel.end(), "\n}")

    vw.end_edit(edit_init)

class OpenMyFileCommand( sublime_plugin.WindowCommand ) :
  def run( self, file ) :
    self.window.open_file(file)

class RepitCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    vw.end_edit(edit)

    edit_begin = vw.begin_edit("repit")
    try:
      lines = vw.sel()
      numLines = len(lines)
      if numLines > 1 :
        reptext = vw.substr(lines[0])
        for i in range(1, numLines) :
          vw.insert(edit, lines[i].begin(), reptext)
    finally:
      vw.end_edit(edit_begin)

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
    edit_init = vw.begin_edit('semicolon_end')
    try:
      for s in vw.sel() :
        line = vw.line(s)
        e = vw.substr(line.b - 1)
        if e == ';' :
          er = sublime.Region(line.b - 1, line.b)
          vw.erase(edit, er)
        else:
          vw.insert(edit, line.b, ";")
    finally:
      vw.end_edit(edit_init)

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

    edit_init = vw.begin_edit('comment_EOL')
    cmnt = self.GetComment(vw.sel()[0].a)
    try:
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
          if rcomment == -1 :
            # c = LineWidth(vw, line, tab_size)
            c = LineWidth(tab_size, lineText)
            target = column - c
#            print "%d - %d = %d" % (column, c, target)

            #Find the end of line and calculate destination column.
            if target <= 0 :
              count = 1
#              print "1 tab"
            else:
              #Round up then sub 1 cuz target is 0 based.
              count = (target + spcs - 2) / spcs
#              print "%d / %d = %d" % (target, spcs, count)

              #Insert number of tabs needed to reach target.
              strng = "\t" * count + cmnt
              vw.insert(edit, line.b, strng)
          else:
            #todo: move the comment in the line to the desired spot.
            cmntCountStr = lineText[:rcomment]
            c = LineWidth(tab_size, cmntCountStr)
#            print "%s width %d" % (cmntCountStr, c)
            target = column - c
            if target < 0 :
              #Figure out how many characters to remove.
              #Loop backwards through the cmntCountStr until
              removeChars = CountFromRight(tab_size, cmntCountStr, target)
#              print "Removing %d" % removeChars
              cmntPnt = line.a + rcomment
              remR = sublime.Region(cmntPnt - removeChars, cmntPnt)
              vw.replace(edit, remR, "")
            elif target > 0 :
              count = (target - 1) / spcs

              #Insert number of tabs needed to reach target.
              strng = "\t" * count
              vw.insert(edit, line.a + rcomment, strng)
          if fst :
            fstColumn = vw.line(s).b
            fst = False

      #add // and move the cursor to the end of the line.
      vw.sel().clear()
      vw.sel().add(sublime.Region(fstColumn, fstColumn))
    finally:
      vw.end_edit(edit_init)

class ShowFileNameCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    self.view.set_status("fname", self.view.name() if self.view.name() else self.view.file_name())
    sublime.set_timeout(self.TurnOff, 4000)

  def TurnOff( self ) :
    self.view.erase_status("fname")

class TestTextCommand( sublime_plugin.TextCommand ) :
  def run( self, edit ) :
    vw = self.view
    for s in vw.sel() :
      lines = vw.lines(s)
      for line in lines :
        b = vw.rowcol(line.a)
        e = vw.rowcol(line.b)
        print "(%d, %d) - (%d, %d)" % (b + e)

class TestWindowCommand( sublime_plugin.WindowCommand ) :
  def __init__( self, window ) :
    super(TestWindowCommand, self).__init__(window)
    self.test = ["g@b.com", "c@y.com", "d@g.com"]

  def run( self ) :
#    self.window.show_quick_panel(self.test, self.OnDone)
    self.window.show_input_panel("test", "", self.OnDone, self.OnChange, None)

  def OnDone( self, Input ) :
    print "Select %s" % Input

  def OnChange( self, Input ) :
    print "Change %s" % Input
    Input = "Hello"

