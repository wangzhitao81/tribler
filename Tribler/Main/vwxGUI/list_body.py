# Written by Niels Zeilemaker
import wx
import wx.lib.scrolledpanel as scrolled

import sys
from threading import currentThread
from traceback import print_stack, print_exc
from time import time
import re

from Tribler.Main.vwxGUI.GuiUtility import GUIUtility
from Tribler.Main.vwxGUI.widgets import NativeIcon, BetterText as StaticText,\
    _set_font, ActionButton

from __init__ import *
from wx._core import PyDeadObjectError
from _abcoll import Iterable

DEBUG = False

class ListItem(wx.Panel):
    
    @warnWxThread
    def __init__(self, parent, parent_list, columns, data, original_data, leftSpacer = 0, rightSpacer = 0, showChange = False, list_selected = LIST_SELECTED, list_expanded = LIST_EXPANDED, list_selected_and_expanded = LIST_DARKBLUE):
        wx.Panel.__init__(self, parent)
         
        self.parent_list = parent_list
        self.columns = columns
        self.data = data
        self.original_data = original_data
         
        self.showChange = showChange
        self.list_deselected = LIST_DESELECTED
        self.list_selected = list_selected
        self.list_expanded = list_expanded
        self.list_selected_and_expanded = list_selected_and_expanded
        
        self.highlightTimer = None
        self.selected = False
        self.expanded = False
        self.expandedPanel = None
        self.SetBackgroundColour(self.list_deselected)
        self.SetForegroundColour(parent_list.GetForegroundColour())
        self.SetFont(parent_list.GetFont())
        
        self.vSizer = wx.BoxSizer(wx.VERTICAL)
        self.hSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.controls = []
        self.AddComponents(leftSpacer, rightSpacer)
        
        self.vSizer.Add(self.hSizer, 0, wx.EXPAND)
        self.SetSizer(self.vSizer)
    
    @warnWxThread
    def AddComponents(self, leftSpacer, rightSpacer):
        if leftSpacer > 0:
            self.hSizer.AddSpacer((leftSpacer, -1))
         
        for i in xrange(len(self.columns)):
            if self.columns[i].get('show', True):
                width = self.columns[i].get('width', wx.LIST_AUTOSIZE)
                if isinstance(width, basestring) and width.endswith('em'):
                    test_string = 'T' * int(self.columns[i]['width'][:-2])
                    width = self.GetTextExtent(test_string)[0]
                    self.columns[i]['width'] = width
                
                if width == wx.LIST_AUTOSIZE:
                    option = 1
                    size = wx.DefaultSize
                else:
                    option = 0
                    size = (self.columns[i]['width'], -1)
                    
                remaining_width = size[0]
                addColumnname = self.columns[i].get('showColumname', True) and self.columns[i].get('name', False)
                type = self.columns[i].get('type', 'label')
                if type == 'label':
                    str_data = self.columns[i].get('fmt', unicode)(self.data[i])
                    
                    prefix = self.columns[i]['name'] + ": " if addColumnname else ''
                    str_data = prefix + str_data
                    
                    control = StaticText(self, style=self.columns[i].get('style',0)|wx.ST_NO_AUTORESIZE|wx.ST_DOTS_END, size=size)
    
                    fontWeight = self.columns[i].get('fontWeight', wx.FONTWEIGHT_NORMAL)
                    fontSize = self.columns[i].get('fontSize', 0)
                    if fontWeight != wx.FONTWEIGHT_NORMAL or fontSize:
                        _set_font(control, size_increment = fontSize, fontweight = fontWeight)
    
                    #niels: wx magic prevents us from passing this string with the constructor, ampersands will not work
                    control.SetLabel(str_data.replace('&', "&&"))
                    
                else:
                    if addColumnname:
                        control = StaticText(self, -1, self.columns[i]['name']+": ", style = self.columns[i].get('style',0)|wx.ST_NO_AUTORESIZE|wx.ST_DOTS_END)
                        self._add_control(control, -1, 0, 0)
                        remaining_width -= control.GetSize()[0]
                    
                    if type == 'method':                  
                        control = self.columns[i]['method'](self, self)
                    
                if control:
                    spacing = 0
                    if isinstance(control, Iterable):
                        control, spacing = control
                    
                    control.icon = self._get_icon(i, 'icon')
                    control.icon_right = self._get_icon(i, 'icon_right')
                    
                    self.controls.append(control)
                    
                    if remaining_width != size[0]:
                        control.SetMinSize((remaining_width, control.GetMinSize()[1]))
                    
                    self._add_control(control, i, option, spacing)
                    
                    if width == wx.LIST_AUTOSIZE:
                        control.SetMinSize((1,-1))
            
                    elif width == LIST_AUTOSIZEHEADER:
                        self.columns[i]['width'] = control.GetSize()[0]
                        if self.parent_list.parent_list.header:
                            self.parent_list.parent_list.header.ResizeColumn(i, self.columns[i]['width'])
                        else:
                            if width != LIST_AUTOSIZEHEADER:
                                self.hSizer.Add((width, -1), 0, wx.LEFT, 3) 

        if rightSpacer > 0:
            self.hSizer.AddSpacer((rightSpacer, -1))
        self.hSizer.Layout()
        
        self.AddEvents(self)
        
    def _add_control(self, control, column_index, option, spacing):
        if column_index != 0:
            self.hSizer.AddSpacer((3, -1))
                    
        if control.icon:
            self.hSizer.Add(control.icon, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 3)
        
        self.hSizer.Add(control, option, wx.RESERVE_SPACE_EVEN_IF_HIDDEN|wx.ALIGN_CENTER_VERTICAL|wx.TOP|wx.BOTTOM, 3+spacing)
        
        if control.icon_right:
            self.hSizer.Add(control.icon_right, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 3)
                    
    def _replace_control(self, old_index, newcontrol):
        oldcontrol = self.controls[old_index]
        self.hSizer.Replace(oldcontrol, newcontrol)
        self.hSizer.Detach(oldcontrol)
        
        if isinstance(oldcontrol, wx.Sizer):
            oldcontrol.ShowItems(False)
            oldcontrol.DeleteWindows()
            oldcontrol.Destroy()
        else:
            oldcontrol.Show(False)
            oldcontrol.Destroy()
            
    def _get_icon(self, column, name="icon", staticbitmap = None):
        icon = None
        if self.columns[column].get(name, False):
            if self.columns[column][name] == 'checkbox' or self.columns[column][name] == 'tree':
                if staticbitmap:
                    staticbitmap.SetBitmap(self.GetIcon(self.columns[column][name], LIST_DESELECTED, 0))
                    staticbitmap.Refresh()
                    icon = staticbitmap
                else:
                    icon = wx.StaticBitmap(self, -1, self.GetIcon(self.columns[column][name], LIST_DESELECTED, 0))
                icon.type = self.columns[column][name]
                
            else:
                icon = self.columns[column][name](self)
                if icon:
                    tooltip = None
                    if isinstance(icon, tuple):
                        icon, tooltip = icon
                    
                    if staticbitmap:
                        staticbitmap.SetBitmap(icon)
                        staticbitmap.Refresh()
                        icon = staticbitmap
                    else:
                        icon = wx.StaticBitmap(self, -1, icon)
                    icon.type = None
                    
                    if tooltip:
                        icon.SetToolTipString(tooltip)
        return icon
    
    @warnWxThread
    def AddEvents(self, control):
        if getattr(control, 'GetWindow', False): #convert sizeritems
            control = control.GetWindow() or control.GetSizer()
        
        if getattr(control, 'Bind', False):
            if not isinstance(control, wx.Button) and not isinstance(control, ActionButton):
                control.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouse)
                control.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            else:
                control.Bind(wx.EVT_ENTER_WINDOW, self.OnMouse)
                control.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouse)
        
        func = getattr(control, 'GetChildren', False)
        if func:
            for child in func():
                self.AddEvents(child)
    
    @warnWxThread  
    def GetIcon(self, icontype, background, state):
        return NativeIcon.getInstance().getBitmap(self, icontype, background, state)
    
    @warnWxThread
    def RefreshData(self, data):
        if DEBUG:
            print >> sys.stderr, "LISTITEM: refreshdata"
            
        if isinstance(data[2], dict): #update original_data
            for key in data[2].keys():
                self.original_data[key] = data[2][key]
        else:
            self.original_data = data[2]
        
        prevData = self.data
        self.data = data[1]
        
        control_index = 0
        
        new_controls = False
        has_changed = False
        
        self.Freeze()
        for i in xrange(len(self.columns)):
            if self.columns[i].get('show', True):
                self.controls[control_index].icon = self._get_icon(i, 'icon', self.controls[control_index].icon)
                self.controls[control_index].icon_right = self._get_icon(i, 'icon_right', self.controls[control_index].icon_right)
                
                addColumnname = self.columns[i].get('showColumname', True) and self.columns[i].get('name', False)
                
                type = self.columns[i].get('type','label')
                if type == 'label':
                    str_data = self.columns[i].get('fmt', unicode)(data[1][i])
                    
                    prefix = self.columns[i]['name'] + ": " if addColumnname else ''
                    str_data = prefix + str_data
                    
                    #niels: we need to escape ampersand to allow them to be visible
                    str_data = str_data.replace('&', "&&")
                    
                    if str_data != self.controls[control_index].GetLabel():
                        self.controls[control_index].SetLabel(str_data)
                        has_changed = True
                    control_index += 1
                
                elif type == 'method':
                    if prevData[i] != data[1][i]:
                        control = self.columns[i]['method'](self, self)
                        
                        if isinstance(control, Iterable):
                            control, _ = control
                        
                        if control:
                            control.icon = self.controls[control_index].icon
                            control.icon_right = self.controls[control_index].icon_right
                            
                            if isinstance(control, wx.Window):
                                control.SetBackgroundColour(self.GetBackgroundColour())
                                
                            self._replace_control(control_index, control)
                            self.controls[control_index] = control
                            new_controls = True
                            has_changed = True
                            
                            self.AddEvents(control)
                    control_index += 1
            
        if new_controls:
            self.hSizer.Layout()
        
        if self.showChange and has_changed:
            self.Highlight()
            
        elif new_controls:
            self.ShowSelected()
        
        self.Thaw()
    
    @warnWxThread
    def Highlight(self, timeout = 3.0, revert = True):
        if self.IsShownOnScreen():
            self.BackgroundColor(LIST_HIGHTLIGHT)

            if revert:
                if self.highlightTimer == None:
                    self.highlightTimer = wx.CallLater(timeout * 1000, self.Revert)
                else:
                    self.highlightTimer.Restart(timeout * 1000)
            return True
        return False
            
    def Revert(self):
        try:
            self.ShowSelected()
            self.highlightTimer = None
            
        except PyDeadObjectError: #PyDeadError
            pass
         
    def ShowSelected(self):
        def IsSelected(control):
            if getattr(control, 'GetWindow', False): #convert sizeritems
                control = control.GetWindow()
                
            if getattr(control, 'selected', False): 
                return True
        
            if getattr(control, 'GetChildren', False): 
                children = control.GetChildren()
                for child in children:
                    if IsSelected(child):
                        return True
            return False
        
        if self.expanded:
            if self.list_expanded:
                if self.GetScreenRect().Contains(wx.GetMousePosition()):
                    self.BackgroundColor(self.list_selected_and_expanded)
                else:
                    self.BackgroundColor(self.list_expanded)
            else:
                self.BackgroundColor(self.list_selected)
        elif IsSelected(self):
            self.BackgroundColor(self.list_selected)
        else:
            self.BackgroundColor(self.list_deselected)
            
    def SetDeselectedColour(self, deselected):
        if deselected.Get() != self.list_deselected.Get():
            self.list_deselected = deselected
            self.ShowSelected()
    
    @warnWxThread
    def BackgroundColor(self, color):
        if self.GetBackgroundColour() != color:
            self.Freeze()
            
            self.SetBackgroundColour(color)
            for child in self.GetChildren():
                child = child.GetWindow() if getattr(child, 'IsWindow', False) and child.IsWindow() else child
                if isinstance(child, wx.Window) and not isinstance(child, wx.Button):
                    child.SetBackgroundColour(color)
            
            for control in self.controls:
                if getattr(control, 'icon', False) and control.icon.type:
                    state = 1 if self.expanded else 0
                    control.icon.SetBitmap(self.GetIcon(control.icon.type, self.GetBackgroundColour(), state))
                    control.icon.Refresh()
            
            #self.Refresh()
            self.Thaw()
            return True
        
        return False
    
    @warnWxThread
    def Deselect(self, raise_event = True):
        if self.GetBackgroundColour() == self.list_selected or self.expanded:
            def SetDeselected(control):
                if getattr(control, 'GetWindow', False): #convert sizeritems
                    control = control.GetWindow()
                
                control.selected = False
                if getattr(control, 'GetChildren', False): 
                    children = control.GetChildren()
                    for child in children:
                        SetDeselected(child)
            
            SetDeselected(self)
            
            if self.expanded:
                self.DoCollapse(raise_event)

            self.ShowSelected()
       
    def GetColumn(self, column):
        return self.data[column]
    
    @warnWxThread
    def OnMouse(self, event):
        if event.Entering():
            event.GetEventObject().selected = True
            wx.CallAfter(self.ShowSelected)
            
        elif event.Leaving():
            event.GetEventObject().selected = False
            wx.CallAfter(self.ShowSelected)
            
        elif event.LeftDown():
            event.listitem = self
            self.parent_list.lastMouseLeftDownEvent = event
        
        elif event.LeftUp():
            if getattr(self.parent_list.lastMouseLeftDownEvent, 'listitem', None) == self:
                self.OnClick(event)
        
        elif event.RightUp():
            self.OnRightClick(event)
        
        elif event.ButtonDClick(wx.MOUSE_BTN_LEFT):
            self.OnDClick(event)
            
        event.Skip() #Allow windows to paint button hover
    
    @warnWxThread
    def OnClick(self, event = None):
        if not self.expanded:
            if self.parent_list.OnExpand(self):
                self.expanded = True
                self.ShowSelected()
            
                for control in self.controls:
                    if control.icon and control.icon.type:
                        control.icon.SetBitmap(self.GetIcon(control.icon.type, self.list_selected, 1))
        else:
            self.DoCollapse()
            
    @warnWxThread
    def OnRightClick(self, event = None):
        pass

    @warnWxThread
    def OnDClick(self, event = None):
        pass
            
    @warnWxThread
    def DoExpand(self):
        if not self.expanded:
            self.OnClick()
    
    @warnWxThread
    def Expand(self, panel):
        self.expandedPanel = panel
        
        if getattr(panel, 'SetCursor', False):
            panel.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            #panel.SetFont(panel.GetDefaultAttributes().font)
        
        panel.Show()
        self.vSizer.Add(panel, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 3)
        self.Layout()
        
    def GetExpandedPanel(self):
        return self.expandedPanel

    @warnWxThread
    def DoCollapse(self, raise_events = True):
        self.parent_list.OnCollapse(self, raise_events = raise_events)
        self.expanded = False
            
        for control in self.controls:
            if control.icon and control.icon.type:
                control.icon.SetBitmap(self.GetIcon(control.icon.type, self.list_selected, 0))

    @warnWxThread
    def Collapse(self):
        if self.expanded:
            self.expanded = False
            self.ShowSelected()
            
            if self.expandedPanel:
                self.expandedPanel.Hide()
                
                self.vSizer.Detach(self.expandedPanel)
                self.vSizer.Layout()
                return self.expandedPanel
        
    def OnEventSize(self, width):
        if self.expanded and self.expandedPanel:
            if getattr(self.expandedPanel, 'OnEventSize', False):
                return self.expandedPanel.OnEventSize(width)
        return False
        
    def __str__( self ):
        return "ListItem " + " ".join(map(str, self.data))
 
class AbstractListBody():
    
    @warnWxThread
    def __init__(self, parent_list, columns, leftSpacer = 0, rightSpacer = 0, singleExpanded = False, showChange = False, list_item_max = None, hasFilter = True, listRateLimit = LIST_RATE_LIMIT):
        self.columns = columns
        self.leftSpacer = leftSpacer
        self.rightSpacer = rightSpacer
        self.parent_list = parent_list
        self.singleExpanded = singleExpanded
        self.showChange = showChange
        self.list_selected = LIST_SELECTED
        self.list_expanded = LIST_EXPANDED
        self.listRateLimit = listRateLimit
        if not list_item_max:
            list_item_max = LIST_ITEM_MAX_SIZE
        self.list_item_max = list_item_max
        self.list_cur_max = self.list_item_max
        
        self.hasFilter = hasFilter
        
        hSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.listpanel = wx.Panel(self, name="LIST")
        
        #vertical sizer containing all items
        self.vSizer = wx.BoxSizer(wx.VERTICAL)
        self.listpanel.SetSizer(self.vSizer)
        hSizer.Add(self.listpanel, 1)
        self.SetSizer(hSizer)
    
        #messagePanel text
        self.messagePanel = wx.Panel(self.listpanel)
        self.messagePanel.SetBackgroundColour(DEFAULT_BACKGROUND)
        self.messagePanel.Show(False)
        messageVSizer = wx.BoxSizer(wx.VERTICAL)
        
        self.headerText = StaticText(self.messagePanel)
        _set_font(self.headerText, fontweight=wx.FONTWEIGHT_BOLD)
        self.messageText = StaticText(self.messagePanel)
        self.loadNext = wx.Button(self.messagePanel)
        self.loadNext.Bind(wx.EVT_BUTTON, self.OnLoadMore)
        self.loadNext.Hide()
        
        messageVSizer.Add(self.headerText, 0, wx.EXPAND)
        messageVSizer.Add(self.messageText, 0, wx.EXPAND)
        messageVSizer.Add(self.loadNext, 0, wx.ALIGN_CENTER)
        self.messageText.sizer = messageVSizer
        self.messageText.altControl = None
        
        messageSizer = wx.BoxSizer(wx.HORIZONTAL)
        messageSizer.AddStretchSpacer()
        messageSizer.Add(messageVSizer, 0, wx.TOP|wx.BOTTOM, 7)
        messageSizer.AddStretchSpacer()
        self.messagePanel.SetSizer(messageSizer)
        
        #vertical scrollrate
        self.rate = None
        
        #states
        self.cur_expanded = None
        
        #quick filter
        self.filter = None
        self.filterMessage = None
            
        #sorting
        self.sortcolumn = None
        
        #queue lists
        self.done = True
        self.lastData = 0
        self.dataTimer = None
        self.data = None
        self.raw_data = None
        self.items = {}
        
        # Allow list-items to store the most recent mouse left-down events:
        self.lastMouseLeftDownEvent = None
        self.curWidth = -1
        self.Bind(wx.EVT_SIZE, self.OnEventSize)
        self.ShowLoading()
    
    @warnWxThread
    def SetBackgroundColour(self, colour):
        wx.Panel.SetBackgroundColour(self, DEFAULT_BACKGROUND)
        self.listpanel.SetBackgroundColour(colour)
    
    @warnWxThread
    def SetStyle(self, font = None, foregroundcolour = None, list_selected = LIST_SELECTED, list_expanded = LIST_EXPANDED):
        if font:
            self.SetFont(font)
        if foregroundcolour:
            self.SetForegroundColour(foregroundcolour)

        self.list_selected = list_selected
        self.list_expanded = list_expanded

    @warnWxThread        
    def OnSort(self, column, reverse):
        self.Scroll(-1, 0)
        
        #Niels: translating between -1 and None conventions
        if column == -1:
            column = None
            
        self.sortcolumn = column
        self.sortreverse = reverse
        
        self.SetData(highlight = False, force = True)
                        
    def DoSort(self):
        def sortby(b, a):
            if a[0] in self.items:
                a = self.items[a[0]].data[self.sortcolumn]
            else:
                a = a[1][self.sortcolumn]
                
            if b[0] in self.items:
                b = self.items[b[0]].data[self.sortcolumn]
            else:
                b = b[1][self.sortcolumn] 
            
            if isinstance(a, basestring):
                a = a.lower()
            if isinstance(b, basestring):
                b = b.lower()
            
            return cmp(a, b)
        
        fixed_positions = []
        
        index = 0
        while index < len(self.data):
            item = self.data[index]
            if len(item) == 5:
                fixed_positions.append((item[-1], item))
                self.data.pop(index)
                continue
            index += 1
            
        if self.sortcolumn != None:
            self.data = sorted(self.data, cmp = sortby, reverse=self.sortreverse)

        fixed_positions.sort()
        for pos, item in fixed_positions:
            self.data.insert(pos, item)
    
    def SetFilter(self, filter, filterMessage, highlight):
        self.filterMessage = filterMessage
        
        if self.filter is not None or filter is not None:
            self.filter = filter
            self.Scroll(-1, 0)
            self.SetData(highlight = highlight)
    
    @warnWxThread
    def OnExpand(self, item, raise_event = False):
        self.Freeze()
        
        if not self.singleExpanded and wx.GetKeyState(wx.WXK_SHIFT):
            pos_from = self.GetItemPos(self.GetItemKey(self.cur_expanded))
            pos_to = self.GetItemPos(self.GetItemKey(item))
            if pos_from != None and pos_to != None:
                pos_min = min(pos_from, pos_to)
                pos_max = max(pos_from, pos_to)
                self.DeselectAll()
                for index, data in enumerate(self.data[pos_min:pos_max+1]):
                    if index+pos_min != pos_to:
                        self.Select(data[0], raise_event = False)

        elif self.singleExpanded or not wx.GetKeyState(wx.WXK_CONTROL):
            if self.cur_expanded:
                self.OnCollapse(self.cur_expanded, from_expand = True)

        panel = self.parent_list.OnExpand(item)
        if panel and not isinstance(panel, bool):
            item.Expand(panel)
            self.OnChange()
            
        self.cur_expanded = item
        self.Thaw()
        return panel
    
    @warnWxThread
    def OnCollapse(self, item = None, raise_events = True, from_expand = False):
        self.Freeze()
        
        if not item:
            item = self.cur_expanded
            
        if item:
            panel = item.Collapse()
            self.parent_list.OnCollapse(item, panel)
            self.cur_expanded = None

        toBeSelected = None        
        if self.singleExpanded or wx.GetKeyState(wx.WXK_CONTROL):        
            #select another still expanded item
            selectedItems = self.GetExpandedItems()
            if selectedItems:
                toBeSelected = selectedItems[0]
                
        else:
            if raise_events:
                #if we're not comming from expand, then this is a click on a previously selected item
                #schedule a expand if we had multiple items selected
                selectedItems = self.GetExpandedItems()
                if len(selectedItems) > 1 and not from_expand:
                    toBeSelected = self.GetItemKey(item), item                    
                    
                self.DeselectAll()

        #use callafter for select to let all expanded boolean flags settle, before yet again selecting this item
        if toBeSelected:
            toBeSelected[1].expanded = False
            wx.CallAfter(self.Select, toBeSelected[0])
           
        self.Thaw()
    
    @warnWxThread
    def OnChange(self, scrollToTop = False):
        if DEBUG:
            print >> sys.stderr, "ListBody: OnChange"
        self.Freeze()
        
        self.vSizer.Layout()
        self.listpanel.Layout()
        self.Layout()
        
        #Determine scrollrate
        nritems = len(self.vSizer.GetChildren())
        if self.rate is None or nritems <= LIST_ITEM_BATCH_SIZE * 3:
            if nritems > 0:
                height = self.vSizer.GetSize()[1]
                self.rate = height / nritems
                if DEBUG:
                    print >> sys.stderr, "ListBody: setting scrollrate to", self.rate
                
                self.SetupScrolling(scrollToTop = scrollToTop, rate_y = self.rate)
            else:
                if DEBUG:
                    print >> sys.stderr, "ListBody: setting scrollrate to default"
                
                self.SetupScrolling(scrollToTop = scrollToTop)
        else:
            if DEBUG:
                print >> sys.stderr, "ListBody: using scrollrate", self.rate
            self.SetupScrolling(scrollToTop = scrollToTop, rate_y = self.rate)
            
        self.Thaw()
    
    @warnWxThread
    def Reset(self):
        if DEBUG:
            print >> sys.stderr, "ListBody: reset"
            
        self.Freeze()
        
        self.filter = None
        self.filterMessage = None
        self.sortcolumn = None
        self.rate = None
        
        self.vSizer.ShowItems(False)
        self.vSizer.Clear()
        for key in self.items.keys():
            self.items[key].Destroy()
            
        if self.dataTimer:
            self.dataTimer.Stop()
            
        self.list_cur_max = self.list_item_max
            
        self.items = {}
        self.data = None
        self.lastData = 0
        self.raw_data = None
        self.ShowLoading()
        self.OnChange()
        self.Thaw()
        
    def Rebuild(self):
        _rawdata = self.raw_data
        self.Reset()
        self.SetData(_rawdata, highlight = False, force = True)
    
    def IsEmpty(self):
        return len(self.items) == 0
    
    def InList(self, key, onlyCreated = True):
        if onlyCreated or not self.data:
            return key in self.items
        
        if key in self.items:
            return True
        return any(curdata[0] == key for curdata in self.data)
    
    @warnWxThread
    def ScrollToEnd(self, scroll_to_end):
        if scroll_to_end:
            self.Scroll(-1, self.vSizer.GetSize()[1])
        else:
            self.Scroll(-1, 0)
        
    @warnWxThread
    def ScrollToNextPage(self, scroll_to_nextpage):
        scroll_pos = self.CalcUnscrolledPosition(0, 0)[1]/self.GetScrollPixelsPerUnit()[1]
        if scroll_to_nextpage:
            scroll_pos = min(scroll_pos + self.GetScrollPageSize(0), self.vSizer.GetSize()[1])
        else:
            scroll_pos = max(scroll_pos - self.GetScrollPageSize(0), 0)
        self.Scroll(-1, scroll_pos)

    @warnWxThread
    def ScrollToId(self, id):
        if id in self.items:
            sy = self.items[id].GetPosition()[1] / self.GetScrollPixelsPerUnit()[1]
            self.Scroll(-1, sy)
    
    @warnWxThread
    def ShowMessage(self, message, header = None, altControl = None):
        if DEBUG:
            print >> sys.stderr, "ListBody: ShowMessage", message

        self.Freeze()
        
        if header:
            self.headerText.SetLabel(header)
            self.headerText.Show()
        else:
            self.headerText.Hide()
        
        self.messageText.SetLabel(message)
        
        if self.messageText.altControl:
            self.messageText.sizer.Detach(self.messageText.altControl)
            if getattr(self.messageText.altControl, 'ShowItems', False):
                self.messageText.altControl.ShowItems(False)
                self.messageText.altControl.Clear(True)
            self.messageText.altControl = None

        if altControl:
            self.messageText.altControl = altControl
            self.messageText.sizer.Insert(2, altControl, 0, wx.EXPAND)
            
        self.loadNext.Hide()
        self.vSizer.ShowItems(False)
        self.vSizer.Clear()

        self.vSizer.Add(self.messagePanel, 0, wx.EXPAND|wx.BOTTOM, 1)
        self.messagePanel.Layout()
        
        if not self.messagePanel.IsShown():
            self.messagePanel.Show()
        
        self.OnChange()
        self.Thaw()
    
    def GetMessage(self):
        header = message = None
        if self.headerText.IsShown():
            header = self.headerText.GetLabel()
            
        if self.messageText.IsShown():
            message = self.messageText.GetLabel()
            
        return header, message

    @warnWxThread
    def ShowLoading(self):
        self.ShowMessage('Loading, please wait.')
    
    @warnWxThread
    def RefreshData(self, key, data):
        if key in self.items:
            if DEBUG:
                print >> sys.stderr, "ListBody: refresh item", self.items[key]
            self.items[key].RefreshData(data)
            
            #forward update to expandedPanel
            panel = self.items[key].GetExpandedPanel()
            if panel and getattr(panel, 'RefreshData', False):
                if DEBUG:
                    print >> sys.stderr, "ListBody: refresh item (Calling expandedPanel refreshdata)", self.items[key]
                
                panel.RefreshData(data)
                
        else:
            self.data.append(data)
            self.CreateItem(key)
    
    @warnWxThread
    def SetData(self, data = None, highlight = None, force = False):
        if DEBUG:
            nr_items = 0
            if data:
                nr_items = len(data)
            print >> sys.stderr, "ListBody: new data", time(), nr_items
        
        if data == None:
            data = self.raw_data
        else:
            self.raw_data = data
            
        assert not data or len(data[0][1]) == len(self.columns), 'Data does not have equal amount of columns %d/%d %s'%(len(data[0][1]), len(self.columns), type(self.parent_list))
            
        if highlight is None:
            highlight = not self.IsEmpty()
        
        def doSetData():
            self.lastData = time()
            self.dataTimer = None
            
            self.__SetData(highlight)
        
        if force:
            if self.dataTimer:
                self.dataTimer.Stop()
            doSetData()
        else:
            diff = time() - (self.listRateLimit + self.lastData)
            call_in = -diff * 1000
            if call_in <= 0:
                doSetData()
            else:
                if self.dataTimer == None:
                    self.dataTimer = wx.CallLater(call_in, doSetData) 
                else:
                    self.dataTimer.Restart(call_in)
        
    def __SetData(self, highlight = True):
        if DEBUG:
            print >> sys.stderr, "ListBody: __SetData", time()
        
        if __debug__ and currentThread().getName() != "MainThread":
            print  >> sys.stderr,"ListBody: __SetData thread",currentThread().getName(),"is NOT MAIN THREAD"
            print_stack()
        
        self.Freeze()
        
        #apply quickfilter
        if self.filter:
            if self.raw_data:
                data = filter(self.filter, self.raw_data)
            else:
                data = None
        else:
            data = self.raw_data
            
        if not data:
            data = []
        if getattr(self.parent_list, 'SetNrResults', None):
            self.parent_list.SetNrResults(len(data))
        
        self.highlightSet = set()
        cur_keys = set(self.items.keys())
        for curdata in data[:self.list_cur_max]:
            key = curdata[0]
            if key not in cur_keys:
                if highlight:
                    self.highlightSet.add(key)
            else:
                cur_keys.discard(key)
        
        #cur_keys now contains all removed items
        for key in cur_keys:
            self.items[key].Show(False)
            self.items[key].Destroy()
            del self.items[key]

        self.data = data
        self.DoSort()
        self.done = False
        
        if len(data) > 0:
            self.vSizer.ShowItems(False)
            self.vSizer.Clear()
            
            self.CreateItems(nr_items_to_create = 3 * LIST_ITEM_BATCH_SIZE)
            
            #Try to yield
            try:
                wx.Yield()
            except:
                pass
            
        elif self.filter and self.filter.__name__ != 'MatchFFilter':
            self.ShowMessage(self.filterMessage(empty = True) + '.')
        
        if self.done:
            self.Unbind(wx.EVT_IDLE) #unbinding unnecessary event handler seems to improve visual performance
        else:
            self.Bind(wx.EVT_IDLE, self.OnIdle)
        
        self.Thaw()
    
    def OnIdle(self, event):
        if not self.done:
            if self.data and len(self.data) > 0:
                self.CreateItems()
            else:
                self.done = True
                
            #idle event also paints search animation, use request more to show this update
            event.RequestMore(not self.done)
            if self.done:
                self.Unbind(wx.EVT_IDLE)

    def OnLoadMore(self, event = None):
        if self.loadNext.IsShown():
            self.loadNext.Disable()
            self.list_cur_max += LIST_ITEM_MAX_SIZE
            
            wx.CallAfter(self.CreateItems)
            self.Bind(wx.EVT_IDLE, self.OnIdle)
        
    def OnLoadAll(self):
        self.loadNext.Disable()
        self.list_cur_max = sys.maxint
        
        wx.CallAfter(self.CreateItems)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
    
    @warnWxThread
    def CreateItem(self, key):
        if not key in self.items and self.data:
            for curdata in self.data:
                if len(curdata) > 3:
                    thiskey, item_data, original_data, create_method = curdata[:4]
                else:
                    thiskey, item_data, original_data = curdata
                    create_method = ListItem
                
                if key == thiskey:
                    self.items[key] = create_method(self.listpanel, self, self.columns, item_data, original_data, self.leftSpacer, self.rightSpacer, showChange = self.showChange, list_selected=self.list_selected, list_expanded = self.list_expanded)
                    
                    if self.messagePanel.IsShown():
                        before = len(self.vSizer.GetChildren()) - 1
                        self.vSizer.Insert(before, self.items[key], 0, wx.EXPAND|wx.BOTTOM, 1)
                    else:
                        self.vSizer.Add(self.items[key], 0, wx.EXPAND|wx.BOTTOM, 1)
                    
                    self.OnChange()
                    break
    
    @warnWxThread
    def CreateItems(self, nr_items_to_create = LIST_ITEM_BATCH_SIZE, nr_items_to_add = None):
        if not nr_items_to_add:
            nr_items_to_add = self.list_cur_max
        
        if DEBUG:
            print >> sys.stderr, "ListBody: Creating items", time()
        
        initial_nr_items_to_add = nr_items_to_add    
        done = True
        didAdd = False
        
        if len(self.data) > 0:
            t1 = time()
            self.Freeze()
            
            #Check if we need to clear vSizer
            self.messagePanel.Show(False)
            self.loadNext.Show(False)
            self.vSizer.Remove(self.messagePanel)
            
            if self.filter and self.filter.__name__ != 'MatchFFilter':
                message = self.filterMessage() + '.'
            else:
                message = ''
            
            revertList = []
            #Add created/cached items
            for curdata in self.data:
                if len(curdata) > 3:
                    key, item_data, original_data, create_method = curdata[:4]
                else:
                    key, item_data, original_data = curdata
                    create_method = ListItem
                
                if nr_items_to_add > 0 and nr_items_to_create > 0:
                    if key not in self.items:
                        try:
                            self.items[key] = create_method(self.listpanel, self, self.columns, item_data, original_data, self.leftSpacer, self.rightSpacer, showChange = self.showChange, list_selected=self.list_selected, list_expanded = self.list_expanded)
                            nr_items_to_create -= 1
                        except:
                            print_exc()
                            self.items[key] = None
                        
                    item = self.items[key]
                    sizer = self.vSizer.GetItem(item) if item else True
                    if not sizer:
                        self.vSizer.Add(item, 0, wx.EXPAND|wx.BOTTOM, 1)
                        item.Show()
                        didAdd = True

                        if key in self.highlightSet:
                            self.highlightSet.remove(key)
                            
                            if item.Highlight(revert = False):
                                revertList.append(key)
                                                
                    nr_items_to_add -= 1
                else:
                    done = nr_items_to_add == 0 or initial_nr_items_to_add == sys.maxint
    
                    if done:
                        if message != '':
                            message = 'Only showing the first %d of %d'%(len(self.vSizer.GetChildren()), len(self.data)) + message[12:] + '\nFurther specify keywords to reduce the number of items, or click the button below.'
                        else:
                            message = 'Only showing the first %d of %d items in this list.'%(len(self.vSizer.GetChildren()), len(self.data))
                            if self.hasFilter:
                                message +='\nSearch within results to reduce the number of items, or click the button below.'
                            
                        remainingItems = min(LIST_ITEM_MAX_SIZE, len(self.data) - len(self.vSizer.GetChildren()))
                        self.loadNext.SetLabel("Show next %d items"%remainingItems)
                        self.loadNext.Enable()
                        self.loadNext.Show()
                    break
           
            if len(message) > 12:
                self.messageText.SetLabel(message)
                
                self.vSizer.Add(self.messagePanel, 0, wx.EXPAND|wx.BOTTOM, 1)
                self.messagePanel.Layout()
                self.messagePanel.Show()
            
            if didAdd:
                self.OnChange()
            self.Thaw()
            
            if len(revertList) > 0:
                wx.CallLater(1000, self.Revert, revertList)
        
        if len(revertList) > 0:
            wx.CallLater(1000, self.Revert, revertList)
        
        self.done = done
        if DEBUG:
            print >> sys.stderr, "List created", len(self.vSizer.GetChildren()),"rows of", len(self.data),"took", time() - t1, "done:", self.done
    
    def GetItem(self, key):
        return self.items[key]
    
    def GetItems(self):
        return self.items.values()
    
    def GetItemPos(self, key):
        # Returns the index of the ListItem belonging to this key
        for i, data in enumerate(self.data):
            if key == data[0]:
                return i
            
    def GetItemKey(self, item):
        for key, curitem in self.items.iteritems():
            if item == curitem:
                return key
    
    @warnWxThread   
    def RemoveItem(self, remove):
        for key, item in self.items.iteritems():
            if item == remove:
                self.RemoveKey(key)
                break
            
    def RemoveKey(self, key):
        self.RemoveKeys([key])
     
    @warnWxThread   
    def RemoveKeys(self, keys):
        _keys = set(keys)
        
        updated = False
        for key in _keys:
            item = self.items.get(key, None)
            if item:
                self.items.pop(key)

                self.vSizer.Detach(item)
                item.Destroy()
                updated = True

        if updated:
            self.OnChange()

        if self.raw_data:
            for i, curdata in enumerate(self.raw_data):
                if curdata[0] in _keys:
                    self.raw_data.pop(i)
                    _keys.discard(curdata[0])
            
                if len(_keys) == 0:
                    break
            
    def GetExpandedItem(self):
        return self.cur_expanded
    
    def GetExpandedItems(self):
        return [(key, item) for key, item in self.items.iteritems() if item.expanded]
    
    @warnWxThread
    def Select(self, key, raise_event = True):
        if self.singleExpanded:
            self.DeselectAll()
        
        #check if we need to create this item on the spot
        if not key in self.items:
            self.CreateItem(key)
            
        if key in self.items:
            if raise_event:
                self.items[key].OnClick(None)
            else:
                self.items[key].expanded = True
                self.cur_expanded = self.items[key]
            
            self.items[key].ShowSelected()
            
    @warnWxThread
    def SelectNextItem(self, next = True):
        item = self.GetExpandedItem()
        if not item:
            return        
        
        key = None
        for k, i in self.items.iteritems():
            if item == i:
                key = k
        
        select = None
        for index, data in enumerate(self.data):
            if data[0] == key:
                if next and len(self.data) > index+1:
                    select = self.data[index+1][0]
                elif not next and index > 0:
                    select = self.data[index-1][0]
                break

        if select:
            cur_scroll = self.CalcUnscrolledPosition(0, 0)[1]/self.GetScrollPixelsPerUnit()[1]
            if next:
                tot_scroll = (self.items[select].GetPosition()[1]+self.items[select].GetSize()[1]+1) / self.GetScrollPixelsPerUnit()[1]
                if tot_scroll - cur_scroll > self.GetScrollPageSize(1):
                    self.Scroll(-1, tot_scroll-self.GetScrollPageSize(1))
            else:
                tot_scroll = self.items[select].GetPosition()[1] / self.GetScrollPixelsPerUnit()[1]
                if tot_scroll - cur_scroll < 0:
                    self.Scroll(-1, tot_scroll)
            self.Select(select, True)
    
    @warnWxThread
    def DeselectAll(self):
        for _, item in self.GetExpandedItems():
            item.Deselect(raise_event = False)
            
    def Revert(self, revertList):
        for key in revertList:
            if key in self.items:
                self.items[key].Revert()
            
    def OnEventSize(self, event):
        width = self.GetSize()[0]
        if width != self.curWidth:
            doOnChange = False
        
            self.Freeze()
            self.curWidth = width
            
            for item in self.items.itervalues():
                if item.OnEventSize(width):
                    doOnChange = True

            if doOnChange:
                self.OnChange()
            
            self.Thaw()
        event.Skip()
 
class ListBody(AbstractListBody, scrolled.ScrolledPanel):
    def __init__(self, parent, parent_list, columns, leftSpacer = 0, rightSpacer = 0, singleExpanded = False, showChange = False, list_item_max = LIST_ITEM_MAX_SIZE, listRateLimit = LIST_RATE_LIMIT):
        scrolled.ScrolledPanel.__init__(self, parent)
        AbstractListBody.__init__(self, parent_list, columns, leftSpacer, rightSpacer, singleExpanded, showChange, listRateLimit=listRateLimit, list_item_max = list_item_max)
        
        homeId = wx.NewId()
        endId = wx.NewId()
        pupId = wx.NewId()
        pdownId = wx.NewId()
        aupId = wx.NewId()
        adownId = wx.NewId()
        self.Bind(wx.EVT_MENU, lambda event: self.ScrollToEnd(False), id = homeId)
        self.Bind(wx.EVT_MENU, lambda event: self.ScrollToEnd(True), id = endId)
        self.Bind(wx.EVT_MENU, lambda event: self.ScrollToNextPage(False), id = pupId)
        self.Bind(wx.EVT_MENU, lambda event: self.ScrollToNextPage(True), id = pdownId)
        self.Bind(wx.EVT_MENU, lambda event: self.SelectNextItem(False), id = aupId)
        self.Bind(wx.EVT_MENU, lambda event: self.SelectNextItem(True), id = adownId)        
        self.Bind(wx.EVT_CHILD_FOCUS, self.OnChildFocus)
        wx.GetTopLevelParent(self).Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        
        accelerators = [(wx.ACCEL_NORMAL, wx.WXK_HOME, homeId)]
        accelerators.append((wx.ACCEL_NORMAL, wx.WXK_END, endId))
        accelerators.append((wx.ACCEL_NORMAL, wx.WXK_PRIOR, pupId))
        accelerators.append((wx.ACCEL_NORMAL, wx.WXK_NEXT, pdownId))
        accelerators.append((wx.ACCEL_NORMAL, wx.WXK_UP, aupId))
        accelerators.append((wx.ACCEL_NORMAL, wx.WXK_DOWN, adownId))
        self.SetAcceleratorTable(wx.AcceleratorTable(accelerators))
        
        self.SetForegroundColour(parent.GetForegroundColour())
        self.SetupScrolling()
        
        TIMER_ID = wx.NewId()
        self.scrollTimer = wx.Timer(self, TIMER_ID)
        self.Bind(wx.EVT_TIMER, self.checkScroll)
        self.processingMousewheel = False
                
    def OnChildFocus(self, event):
        pass

    def OnMouseWheel(self, event):
        try:
            if self.processingMousewheel:
                return
            self.processingMousewheel = True
            if self.IsShownOnScreen() and self.GetScreenRect().Contains(wx.GetMousePosition()):
                self.GetEventHandler().ProcessEvent(event)
                self.processingMousewheel = False
            else:
                self.processingMousewheel = False
                event.Skip()
                
        except PyDeadObjectError:
            GUIUtility.getInstance().frame.Unbind(wx.EVT_MOUSEWHEEL, handler = self.OnMouseWheel)
  
        
    def Show(self, show = True):
        scrolled.ScrolledPanel.Show(self, show)
        if show:
            self.scrollTimer.Start(1000)
        else:
            self.scrollTimer.Stop()
            
    def checkScroll(self, event):
        maxY = self.vSizer.GetSize()[1]
        doMore = maxY * 0.8
        
        height = self.GetClientSize()[1]
        viewY = self.CalcUnscrolledPosition(list(self.GetViewStart()))[1] + height
        
        if viewY > doMore:
            self.OnLoadMore()
    
class FixedListBody(wx.Panel, AbstractListBody):
    def __init__(self, parent, parent_list, columns, leftSpacer = 0, rightSpacer = 0, singleExpanded = False, showChange = False, list_item_max = LIST_ITEM_MAX_SIZE):
        wx.Panel.__init__(self, parent)
        AbstractListBody.__init__(self, parent_list, columns, leftSpacer, rightSpacer, singleExpanded, showChange, list_item_max = list_item_max, hasFilter = False)
        
        self.SetForegroundColour(parent.GetForegroundColour())
    
    def Scroll(self, x, y):
        pass
    def SetupScrolling(self, scroll_x=True, scroll_y=True, rate_x=20, rate_y=20, scrollToTop=True):
        pass
    def GetScrollPixelsPerUnit(self):
        return [0,0]
 
