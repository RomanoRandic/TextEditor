import tkinter as tk
from tkinter import filedialog
from abc import ABC, abstractmethod
import tkinter.messagebox as messagebox
import importlib.util
import os
import sys
import inspect

class Plugin(ABC):
    @abstractmethod
    def getName(self):
        pass

    @abstractmethod
    def getDescription(self):
        pass

    @abstractmethod
    def execute(self, model, undoManager, clipboardStack):
        pass
class EditAction:
    def execute_do(self):
        pass

    def execute_undo(self):
        pass
    
class UndoObserver:
    def updateUndoStatus(self, canUndo, canRedo):
        pass
class Location:
    def __init__(self, row, column):
        self.row = row
        self.column = column
    def __repr__(self):
        return f"Location(row={self.row}, column={self.column})"


class LocationRange:
    def __init__(self, start: Location, end: Location):
        self.start = start
        self.end = end
    def __repr__(self):
        return f"LocationRange(start={self.start}, end={self.end})"
class UndoManager:
    _instance = None

    def __init__(self):
        if UndoManager._instance is not None:
            raise Exception("This is a singleton!")
        self.undoStack = []
        self.redoStack = []
        self.observers = []
        UndoManager._instance = self

    @staticmethod
    def get_instance():
        if UndoManager._instance is None:
            UndoManager()
        return UndoManager._instance

    def undo(self):
        if self.undoStack:
            action = self.undoStack.pop()
            action.execute_undo()
            self.redoStack.append(action)
            self.notify_observers()

    def redo(self):
        if self.redoStack:
            action = self.redoStack.pop()
            action.execute_do()
            self.undoStack.append(action)
            self.notify_observers()

    def push(self, action: EditAction):
        self.redoStack.clear()
        self.undoStack.append(action)
        self.notify_observers()

    def add_observer(self, observer: UndoObserver):
        self.observers.append(observer)

    def remove_observer(self, observer: UndoObserver):
        self.observers.remove(observer)

    def notify_observers(self):
        canUndo = len(self.undoStack) > 0
        canRedo = len(self.redoStack) > 0
        for observer in self.observers:
            observer.updateUndoStatus(canUndo, canRedo)
class InsertCharacterAction(EditAction):
    def __init__(self, model, char, location: Location):
        self.model = model
        self.char = char
        self.location = Location(location.row, location.column)
        self.after_text = ""

    def execute_do(self):
        self.model.cursorLocation = Location(self.location.row, self.location.column)
        if self.char == '\n':
            line = self.model.lines[self.location.row]
            self.after_text = line[self.location.column:] 
        self.model.insert_char(self.char)

    def execute_undo(self):
        if self.char == '\n':
            row = self.location.row
            col = self.location.column

            self.model.cursorLocation = Location(row, col)

            self.model.lines[row] = self.model.lines[row] + self.model.lines[row + 1]
            del self.model.lines[row + 1]

            self.model.setSelectionRange(None)
            self.model.notify_textObservers()
            self.model.notify_cursorObservers(self.model.cursorLocation)
        else:
            self.model.cursorLocation = Location(self.location.row, self.location.column)
            self.model.delete_after()






class DeleteRangeAction(EditAction):
    def __init__(self, model, range_: LocationRange, deleted_text: str):
        self.model = model
        self.range = range_
        self.deleted_text = deleted_text

    def execute_do(self):
        self.model.setSelectionRange(self.range)
        self.model.deleteRange()

    def execute_undo(self):
        self.model.cursorLocation = Location(self.range.start.row, self.range.start.column)
        self.model.insert_text(self.deleted_text)
class DeleteBeforeAction(EditAction):
    def __init__(self, model):
        self.model = model
        self.location = Location(model.cursorLocation.row, model.cursorLocation.column)
        self.deleted_char = ""

    def execute_do(self):
        row = self.location.row
        col = self.location.column
        if col == 0 and row > 0:
            self.deleted_char = "\n"
        else:
            line = self.model.lines[row]
            self.deleted_char = line[col - 1]
        self.model.cursorLocation = Location(row, col)
        self.model.delete_before()

    def execute_undo(self):
        self.model.cursorLocation = Location(self.location.row, self.location.column)
        self.model.insert_char(self.deleted_char)

class DeleteAfterAction(EditAction):
    def __init__(self, model):
        self.model = model
        self.location = Location(model.cursorLocation.row, model.cursorLocation.column)
        self.deleted_char = ""

    def execute_do(self):
        row = self.location.row
        col = self.location.column
        line = self.model.lines[row]
        if col == len(line) and row < len(self.model.lines) - 1:
            self.deleted_char = "\n"
        else:
            self.deleted_char = line[col]
        self.model.cursorLocation = Location(row, col)
        self.model.delete_after()

    def execute_undo(self):
        self.model.cursorLocation = Location(self.location.row, self.location.column)
        self.model.insert_char(self.deleted_char)


class ClipboardObserver:
    def updateClipboard(self):
        pass

class ClipboardStack:
    def __init__(self):
        self.texts = []
        self.observers = []

    def push(self, text: str):
        self.texts.append(text)
        self.notify_observers()

    def pop(self):
        if self.texts:
            text = self.texts.pop()
            self.notify_observers()
            return text
        return ""

    def peek(self):
        if self.texts:
            return self.texts[-1]
        return ""

    def is_empty(self):
        return len(self.texts) == 0

    def clear(self):
        self.texts.clear()
        self.notify_observers()

    def add_observer(self, observer: ClipboardObserver):
        self.observers.append(observer)

    def remove_observer(self, observer: ClipboardObserver):
        self.observers.remove(observer)

    def notify_observers(self):
        for observer in self.observers:
            observer.updateClipboard()



class CursorObserver:
    def __init__(self, editor_canvas: tk.Canvas, line_height: int, char_width: int):
        self.canvas = editor_canvas
        self.line_height = line_height
        self.char_width = char_width

    def update(self, loc: Location):
        self.canvas.delete("cursor")
        cursor_x = 5 + self.char_width * loc.column
        cursor_y = loc.row * self.line_height
        self.canvas.create_line(cursor_x, cursor_y,
                                cursor_x, cursor_y + self.line_height, fill="red", width=2, tag="cursor")
class TextObserver:
    def __init__(self, editor_canvas: tk.Canvas, model, line_height: int, char_width: int):
        self.canvas = editor_canvas
        self.model = model  
        self.line_height = line_height
        self.char_width = char_width


    def update(self, lines: list[str]):
        self.canvas.delete("text")

        selection = self.model.getSelectionRange()

        for i, line in enumerate(lines):
            if selection and selection.start.row <= i <= selection.end.row:
                start_col = 0
                end_col = len(line)

                if i == selection.start.row:
                    start_col = selection.start.column
                if i == selection.end.row:
                    end_col = selection.end.column

                for col in range(start_col, end_col):
                    if col >= len(line):
                        break
                    x1 = 5 + col * self.char_width
                    y1 = i * self.line_height
                    x2 = x1 + self.char_width
                    y2 = y1 + self.line_height
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="yellow", outline="", tags="text")

            self.canvas.create_text(5, (i) * self.line_height, anchor="nw",
                                    text=line, font=("Courier", 12), tags="text")

            

class TextEditorModel:
    def __init__(self, text: str):
        self.lines = text.split('\n')
        self.selectionRange = None
        self.cursorObservers = []
        self.textObservers = []
        self.cursorLocation = Location(0,0)
        
        
    def add_textObserver (self, observer:TextObserver):
        self.textObservers.append(observer)
    def remove_textObserver(self, observer: TextObserver):
        self.textObservers.remove(observer)
    def notify_textObservers(self):
        for observer in self.textObservers:
            observer.update(self.lines)

    def add_cursorObserver (self, observer: CursorObserver):
        self.cursorObservers.append(observer)

    def remove_cursorObserver(self, observer: CursorObserver):
        self.CursorObservers.remove(observer)
    def notify_cursorObservers(self,loc:Location):
        for observer in self.cursorObservers:
            observer.update(loc)
    def delete_before (self):
        if (self.cursorLocation.column>0):
            new_lines = self.lines[self.cursorLocation.row][:self.cursorLocation.column-1]+self.lines[self.cursorLocation.row][self.cursorLocation.column:]
            self.lines[self.cursorLocation.row] = new_lines
            self.notify_textObservers()

            self.move_cursor_left()
        elif (len(self.lines)>self.cursorLocation.row>0):
            after = Location(self.cursorLocation.row-1, len(self.lines[self.cursorLocation.row-1]))
            self.lines[self.cursorLocation.row-1]+=self.lines[self.cursorLocation.row]
            self.lines.remove(self.lines[self.cursorLocation.row])
            self.notify_textObservers()
            self.cursorLocation = after
            self.notify_cursorObservers(self.cursorLocation)
                
    def delete_after(self):
            if (self.cursorLocation.column<len(self.lines[self.cursorLocation.row])):
                new_lines = self.lines[self.cursorLocation.row][:self.cursorLocation.column]+self.lines[self.cursorLocation.row][self.cursorLocation.column+1:]
                self.lines[self.cursorLocation.row] = new_lines
                self.notify_textObservers()

                
    def deleteRange(self):
        r=self.getSelectionRange()
        start = r.start
        end = r.end
        
        if start.row == end.row:
            line = self.lines[start.row]
            new_line = line[:start.column] + line[end.column:]
            self.lines[start.row] = new_line
        else:
            first_line_part = self.lines[start.row][:start.column]
            last_line_part = self.lines[end.row][end.column:]
            self.lines[start.row] = first_line_part + last_line_part
            
            for i in range(end.row, start.row, -1):
                del self.lines[i]
        
        self.cursorLocation = Location(start.row, start.column)
        self.cursorLocation = r.start
        self.setSelectionRange(None)
        self.notify_textObservers()
        self.notify_cursorObservers(self.cursorLocation)
        
    def setSelectionRange(self, range:LocationRange):
        self.selectionRange = range
    def getSelectionRange(self):
        return self.selectionRange
        
    
            
        
    def move_cursor_left(self):
        if self.cursorLocation.column > 0:
            self.cursorLocation.column -= 1
            self.notify_cursorObservers(self.cursorLocation)
        elif self.cursorLocation.row > 0:
            self.cursorLocation.row -= 1
            self.cursorLocation.column = len(self.lines[self.cursorLocation.row])
            self.notify_cursorObservers(self.cursorLocation)

    def move_cursor_right(self):
        if self.cursorLocation.column < len(self.lines[self.cursorLocation.row]):
            self.cursorLocation.column += 1
            self.notify_cursorObservers(self.cursorLocation)
        elif self.cursorLocation.row < len(self.lines) - 1:
            self.cursorLocation.row += 1
            self.cursorLocation.column = 0
            self.notify_cursorObservers(self.cursorLocation)

    def move_cursor_up(self):
        if self.cursorLocation.row > 0:
            self.cursorLocation.row -= 1
            self.cursorLocation.column = min(self.cursorLocation.column, len(self.lines[self.cursorLocation.row]))
            self.notify_cursorObservers(self.cursorLocation)
    def move_cursor_down(self):
        if self.cursorLocation.row < len(self.lines) - 1:
            self.cursorLocation.row += 1
            self.cursorLocation.column = min(self.cursorLocation.column, len(self.lines[self.cursorLocation.row]))
            self.notify_cursorObservers(self.cursorLocation)
    def iteratorAllLines(self):
        for i, line in enumerate(self.lines):
            yield i, line
            
    def iteratorLinesRange(self, index1: int, index2:int):
        for i, line in enumerate(self.lines[index1:index2], start=index1):
            yield i, line           
    def insert_char(self, c):
        if self.selectionRange is not None:
            self.deleteRange()

        row = self.cursorLocation.row
        col = self.cursorLocation.column
        line = self.lines[row]
        
        if c == '\n':  
            before = line[:col]
            after = line[col:]
            self.lines[row] = before
            self.lines.insert(row + 1, after)
            self.cursorLocation.row += 1
            self.cursorLocation.column = 0
        else:
            new_line = line[:col] + c + line[col:]
            self.lines[row] = new_line
            self.cursorLocation.column += 1

        self.setSelectionRange(None)
        self.notify_textObservers()
        self.notify_cursorObservers(self.cursorLocation)

    def insert_text(self, text):
        for c in text:
            self.insert_char(c)

class TextEditor(tk.Canvas):
    def __init__(self, master, model: TextEditorModel, **kwargs):
        super().__init__(master, **kwargs)
        self.model = model
        self.line_height = 20
        self.char_width = 10
        self.font = ("Courier", 12)
        self.cursorObserver = CursorObserver(self, self.line_height, self.char_width)
        self.model.add_cursorObserver(self.cursorObserver)
        self.textObserver = TextObserver(self, self.model, self.line_height, self.char_width)
        self.model.add_textObserver(self.textObserver)
        self.clipboard = ClipboardStack()
     
        self.bind("<Key>", self.on_key_press)
        self.focus_set()
        self.draw()
        menubar = tk.Menu(master)
        master.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=master.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        self.edit_menu = tk.Menu(menubar, tearoff=0)
        self.edit_menu.add_command(label="Undo", command=self.undo, state="disabled")
        self.edit_menu.add_command(label="Redo", command=self.redo, state="disabled")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", command=self.cut, state="disabled")
        self.edit_menu.add_command(label="Copy", command=self.copy, state="disabled")
        self.edit_menu.add_command(label="Paste", command=self.paste, state="disabled")
        self.edit_menu.add_command(label="Paste and Take", command=self.paste_and_take, state="disabled")
        self.edit_menu.add_command(label="Delete selection", command=self.delete_selection, state="disabled")
        self.edit_menu.add_command(label="Clear document", command=self.clear_document)
        menubar.add_cascade(label="Edit", menu=self.edit_menu)

        move_menu = tk.Menu(menubar, tearoff=0)
        move_menu.add_command(label="Cursor to document start", command=self.cursor_to_start)
        move_menu.add_command(label="Cursor to document end", command=self.cursor_to_end)
        menubar.add_cascade(label="Move", menu=move_menu)

        toolbar = tk.Frame(master, bd=1, relief=tk.RAISED)
        self.undo_button = tk.Button(toolbar, text="Undo", command=self.undo, state="disabled")
        self.redo_button = tk.Button(toolbar, text="Redo", command=self.redo, state="disabled")
        self.cut_button = tk.Button(toolbar, text="Cut", command=self.cut, state="disabled")
        self.copy_button = tk.Button(toolbar, text="Copy", command=self.copy, state="disabled")
        self.paste_button = tk.Button(toolbar, text="Paste", command=self.paste, state="disabled")

        self.undo_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.redo_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.cut_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.copy_button.pack(side=tk.LEFT, padx=2, pady=2)
        self.paste_button.pack(side=tk.LEFT, padx=2, pady=2)

        toolbar.pack(side=tk.TOP, fill=tk.X)
        self.statusbar = tk.Label(master, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.update_statusbar()
        self.plugins = []
        self.plugins_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Plugins", menu=self.plugins_menu)


        UndoManager.get_instance().add_observer(self)
        self.clipboard.add_observer(self)
        self.load_plugins()


        
    def load_plugins(self):
        plugins_folder = "plugins"

        if not os.path.exists(plugins_folder):
            os.makedirs(plugins_folder)

        sys.path.insert(0, plugins_folder)

        for filename in os.listdir(plugins_folder):
            if filename.endswith(".py"):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(module_name)
                except Exception as e:
                    print(f"Ne mogu ucitati modul {module_name}: {e}")
                    continue

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if hasattr(obj, "getName") and hasattr(obj, "getDescription") and hasattr(obj, "execute"):
                        try:
                            plugin_instance = obj()
                            self.plugins.append(plugin_instance)
                            self.plugins_menu.add_command(
                                label=plugin_instance.getName(),
                                command=lambda p=plugin_instance: p.execute(self.model, UndoManager.get_instance(), self.clipboard)
                            )
                        except Exception as e:
                            print(f"Ne mogu instancirati plugin {name}: {e}")

    def open_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not filepath:
            return
        with open(filepath, "r", encoding="utf-8") as file:
            content = file.read()
        self.model.lines = content.split('\n')
        self.model.cursorLocation = Location(0, 0)
        self.model.setSelectionRange(None)
        self.model.notify_textObservers()
        self.model.notify_cursorObservers(self.model.cursorLocation)

    def save_file(self):
        filepath = filedialog.asksaveasfilename(defaultextension="txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not filepath:
            return
        with open(filepath, "w", encoding="utf-8") as file:
            file.write('\n'.join(self.model.lines))
           
    def update_statusbar(self):
        row = self.model.cursorLocation.row + 1
        col = self.model.cursorLocation.column + 1
        total_lines = len(self.model.lines)
        self.statusbar.config(text=f"Ln {row}, Col {col}    Total lines: {total_lines}")

        
    def updateUndoStatus(self, canUndo, canRedo):
        state_undo = "normal" if canUndo else "disabled"
        state_redo = "normal" if canRedo else "disabled"

        self.undo_button.config(state=state_undo)
        self.redo_button.config(state=state_redo)
        self.edit_menu.entryconfig("Undo", state=state_undo)
        self.edit_menu.entryconfig("Redo", state=state_redo)

    def updateClipboard(self):
        state_paste = "normal" if not self.clipboard.is_empty() else "disabled"

        self.paste_button.config(state=state_paste)
        self.edit_menu.entryconfig("Paste", state=state_paste)
        self.edit_menu.entryconfig("Paste and Take", state=state_paste)

    def updateSelectionDependentItems(self):
        has_selection = self.model.getSelectionRange() is not None

        state_sel = "normal" if has_selection else "disabled"
        self.cut_button.config(state=state_sel)
        self.copy_button.config(state=state_sel)
        self.edit_menu.entryconfig("Cut", state=state_sel)
        self.edit_menu.entryconfig("Copy", state=state_sel)
        self.edit_menu.entryconfig("Delete selection", state=state_sel)

    def undo(self):
        UndoManager.get_instance().undo()

    def redo(self):
        UndoManager.get_instance().redo()

    def cut(self):
        if self.model.getSelectionRange() is not None:
            selected_text = self.get_selected_text()
            self.clipboard.push(selected_text)
            action = DeleteRangeAction(self.model, self.model.getSelectionRange(), selected_text)
            UndoManager.get_instance().push(action)
            action.execute_do()

    def copy(self):
        if self.model.getSelectionRange() is not None:
            selected_text = self.get_selected_text()
            self.clipboard.push(selected_text)

    def paste(self):
        text = self.clipboard.peek()
        self.model.insert_text(text)

    def paste_and_take(self):
        text = self.clipboard.pop()
        self.model.insert_text(text)

    def delete_selection(self):
        if self.model.getSelectionRange() is not None:
            selected_text = self.get_selected_text()
            action = DeleteRangeAction(self.model, self.model.getSelectionRange(), selected_text)
            UndoManager.get_instance().push(action)
            action.execute_do()

    def clear_document(self):
        self.model.lines = [""]
        self.model.cursorLocation = Location(0, 0)
        self.model.setSelectionRange(None)
        self.model.notify_textObservers()
        self.model.notify_cursorObservers(self.model.cursorLocation)

    def cursor_to_start(self):
        self.model.cursorLocation = Location(0, 0)
        self.model.setSelectionRange(None)
        self.model.notify_cursorObservers(self.model.cursorLocation)

    def cursor_to_end(self):
        last_row = len(self.model.lines) - 1
        last_col = len(self.model.lines[last_row])
        self.model.cursorLocation = Location(last_row, last_col)
        self.model.setSelectionRange(None)
        self.model.notify_cursorObservers(self.model.cursorLocation)

    def get_selected_text(self):
        selection = self.model.getSelectionRange()
        if selection is None:
            return ""

        lines = self.model.lines
        start = selection.start
        end = selection.end

        if start.row == end.row:
            return lines[start.row][start.column:end.column]
        else:
            selected_text = lines[start.row][start.column:] + "\n"
            for row in range(start.row + 1, end.row):
                selected_text += lines[row] + "\n"
            selected_text += lines[end.row][:end.column]
            return selected_text

    def handle_shift_movement(self, move_function):
        selection = self.model.getSelectionRange()

        if selection is None:
            loc = Location(self.model.cursorLocation.row, self.model.cursorLocation.column)
            move_function()
            new_loc = self.model.cursorLocation
            if new_loc.row<loc.row or new_loc.column<loc.column:
                self.model.setSelectionRange(LocationRange( new_loc,loc))

            else:
                self.model.setSelectionRange(LocationRange(loc, new_loc))
        else:
            if self.model.getSelectionRange().start == self.model.cursorLocation:
                loc = self.model.getSelectionRange().end
            else:
                loc = self.model.getSelectionRange().start
            move_function()
            new_loc = self.model.cursorLocation
            if (new_loc.row < loc.row) or (new_loc.row == loc.row and new_loc.column < loc.column):
                self.model.setSelectionRange(LocationRange( new_loc,loc))

            else:
                self.model.setSelectionRange(LocationRange(loc, new_loc))
        self.model.notify_textObservers()

    def draw(self):
        self.delete("all")
        iterator = self.model.iteratorAllLines()
        for i, line in iterator:
            self.create_text(5, (i) * self.line_height, anchor="nw",
                             text=line, font=self.font, tag="text")
        self.model.notify_cursorObservers(self.model.cursorLocation)



    def on_key_press(self, event):
        key = event.keysym
        if (key == "Delete" or key == "BackSpace") and self.model.getSelectionRange() is not None:
            selected_text = self.get_selected_text()
            action = DeleteRangeAction(self.model, self.model.getSelectionRange(), selected_text)
            UndoManager.get_instance().push(action)
            action.execute_do()

        elif key == "Delete":
            action = DeleteAfterAction(self.model)
            UndoManager.get_instance().push(action)
            action.execute_do()

        elif key == "BackSpace":
            action = DeleteBeforeAction(self.model)
            UndoManager.get_instance().push(action)
            action.execute_do()

        elif key == "Left":
            if (event.state & 0x0001):
                self.handle_shift_movement(self.model.move_cursor_left)
            else:
                self.model.setSelectionRange(None)
                self.model.move_cursor_left()
                self.model.notify_textObservers()
        elif key == "Right":
            if (event.state & 0x0001):
                self.handle_shift_movement(self.model.move_cursor_right)
            else:
                self.model.setSelectionRange(None)
                self.model.move_cursor_right()
                self.model.notify_textObservers()
        elif key == "Up":
            if (event.state & 0x0001):
                self.handle_shift_movement(self.model.move_cursor_up)
            else:
                self.model.setSelectionRange(None)
                self.model.move_cursor_up()
                self.model.notify_textObservers()
        elif key == "Down":
            if (event.state & 0x0001):
                self.handle_shift_movement(self.model.move_cursor_down)
            else:
                self.model.setSelectionRange(None)
                self.model.move_cursor_down()
                self.model.notify_textObservers()
                
        elif (event.state & 0x0004) and key == 'c' and self.model.getSelectionRange() is not None:
            selected_text = self.get_selected_text()
            self.clipboard.push(selected_text)
            
        elif (event.state & 0x0004) and key == 'x' and self.model.getSelectionRange() is not None:
            selected_text = self.get_selected_text()
            self.clipboard.push(selected_text)
            self.model.deleteRange()
            
        elif (event.state & 0x0004) and key == 'v' and not (event.state & 0x0001):
            text = self.clipboard.peek()
            self.model.insert_text(text)
            
        elif (event.state & 0x0004) and (event.state & 0x0001) and key.lower() == 'v':
            text = self.clipboard.pop()
            self.model.insert_text(text)
            
        elif key == 'Return':
            loc = Location(self.model.cursorLocation.row, self.model.cursorLocation.column)
            action = InsertCharacterAction(self.model, '\n', loc)
            UndoManager.get_instance().push(action)
            action.execute_do()

                    
        elif (event.state & 0x0004) and key.lower() == 'z':
            UndoManager.get_instance().undo()

        elif (event.state & 0x0004) and key.lower() == 'y':
            UndoManager.get_instance().redo()

        elif len(event.char) == 1 and event.char.isprintable():
            loc = Location(self.model.cursorLocation.row, self.model.cursorLocation.column)
            action = InsertCharacterAction(self.model, event.char, loc)
            UndoManager.get_instance().push(action)
            action.execute_do()
        self.model.notify_cursorObservers(self.model.cursorLocation)
        self.update_statusbar()

        self.updateClipboard()
        self.updateUndoStatus(len(UndoManager.get_instance().undoStack) > 0,
                              len(UndoManager.get_instance().redoStack) > 0)
        self.updateSelectionDependentItems()




        


root = tk.Tk()
root.title("TextEditor")

initial_text = "Ovo je prvi redak.\nOvo je drugi redak.\nI treći red je ovdje."
model = TextEditorModel(initial_text)

editor = TextEditor(root, model, width=600, height=400, bg="white")
editor.pack(fill="both", expand=True)

root.mainloop()
