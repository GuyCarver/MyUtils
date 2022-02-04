""" Sublime Text plugin to show sope of character under cursor. """

import sublime, sublime_plugin

showsyntax = False

class ToggleSyntaxCommand( sublime_plugin.ApplicationCommand ):

  #Called by menu system to show check mark or not as this menu item has the "checkbox": true flag
  def is_checked( self ):
    return showsyntax

  def run( self ):
    ''' Toggle the showsyntax global. '''
    global showsyntax
    showsyntax = not showsyntax
#    print("Syntax set to", showsyntax)
    return showsyntax

#--------------------------------------------------------
class SyntaxScopeCommand(sublime_plugin.ViewEventListener):

  def on_hover( self, aPoint, aZone ):
    ''' When mouse hovers over text, we show a popup of the syntax of the text. '''
    if (not showsyntax) or (aZone != sublime.HOVER_TEXT):
      return

    vw = self.view

    #Don't show tooltip for white spaces.
    text = vw.substr(vw.word(aPoint)).strip()
    if len(text):
      sel = vw.scope_name(aPoint)

      if len(sel):
        vw.show_popup(sel, flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
         location = aPoint, max_width = 600, on_navigate = self.OnNavigate)

  def OnNavigate( self ):
    '''  '''
    self.view.hide_popup()


