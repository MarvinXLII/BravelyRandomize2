import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from release import RELEASE
import hjson
import random
import os
import shutil
import glob
import sys
sys.path.append('src')
from Utilities import get_filename
from randomize import SWITCH, STEAM
from ROM import ROM_SWITCH, ROM_PC

MAIN_TITLE = f"Bravely Randomize 2 v{RELEASE}"

# Source: https://www.daniweb.com/programming/software-development/code/484591/a-tooltip-class-for-tkinter
class CreateToolTip(object):
    '''
    create a tooltip for a given widget
    '''
    def __init__(self, widget, text='widget info', wraplength=200):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.wraplength = wraplength

    def enter(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 30
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                      background='white', relief='solid', borderwidth=1,
                      wraplength=self.wraplength,
                      font=("times", "12", "normal"),
                      padx=4, pady=6,
        )
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()


class GuiApplication:
    def __init__(self, settings=None):
        self.master = tk.Tk()
        self.master.geometry('690x580')
        self.master.title(MAIN_TITLE)
        self.initialize_gui()
        self.initialize_settings(settings)
        self.master.mainloop()


    def initialize_gui(self):

        self.warnings = []
        self.togglers = []
        self.settings = {}
        self.settings['release'] = tk.StringVar()
        self.settings['system'] = tk.StringVar()
        self.rom = None

        with open(get_filename('json/gui.json'), 'r') as file:
            fields = hjson.loads(file.read())

        #####################
        # PAKS FOLDER STUFF #
        #####################

        labelfonts = ('Helvetica', 14, 'bold')
        lf = tk.LabelFrame(self.master, text='Folder', font=labelfonts)
        lf.grid(row=0, columnspan=2, sticky='nsew', padx=5, pady=5, ipadx=5, ipady=5)

        # Path to paks
        self.settings['rom'] = tk.StringVar()
        self.settings['rom'].set('')

        pathToPak = tk.Entry(lf, textvariable=self.settings['rom'], width=65, state='readonly')
        pathToPak.grid(row=0, column=0, columnspan=2, padx=(10,0), pady=3)

        pathLabel = tk.Label(lf, text='Path to "Paks" folder')
        pathLabel.grid(row=1, column=0, sticky='w', padx=5, pady=2)

        pathButton = tk.Button(lf, text='Browse ...', command=self.getPakFile, width=20) # needs command..
        pathButton.grid(row=1, column=1, sticky='e', padx=5, pady=2)
        self.buildToolTip(pathButton,
                          """
Input the game folder labelled "Paks".\n
On Switch the folder name will be something like \nSunrise-E\Content\Paks.\n
On Steam the folder name will be something like \nC:\\Program Files\Steam\steamapps\common\BRAVELY DEFAULT II\Bravely Default II\Content\Paks\n
                          """
                          , wraplength=500)

        #####################
        # SEED & RANDOMIZER #
        #####################

        lf = tk.LabelFrame(self.master, text="Seed", font=labelfonts)
        lf.grid(row=0, column=2, columnspan=2, sticky='nsew', padx=5, pady=5, ipadx=5, ipady=5)
        self.settings['seed'] = tk.IntVar()
        self.randomSeed()

        box = tk.Spinbox(lf, from_=0, to=1e8, width=9, textvariable=self.settings['seed'])
        box.grid(row=2, column=0, sticky='e', padx=60)

        seedBtn = tk.Button(lf, text='Random Seed', command=self.randomSeed, width=12, height=1)
        seedBtn.grid(row=3, column=0, columnspan=1, sticky='we', padx=30, ipadx=30)

        self.randomizeBtn = tk.Button(lf, text='Randomize', command=self.randomize, height=1)
        self.randomizeBtn.grid(row=4, column=0, columnspan=1, sticky='we', padx=30, ipadx=30)

        ############
        # SETTINGS #
        ############

        # Tabs setup
        tabControl = ttk.Notebook(self.master)
        tabNames = ['Settings']
        tabs = {name: ttk.Frame(tabControl) for name in tabNames}
        for name, tab in tabs.items():
            tabControl.add(tab, text=name)
        tabControl.grid(row=2, column=0, columnspan=20, sticky='news')

        # Tab label
        for name, tab in tabs.items():
            labelDict = fields[name]
            for i, (key, value) in enumerate(labelDict.items()):
                row = i % 2
                column = i // 2
                # Setup LabelFrame
                lf = tk.LabelFrame(tab, text=key, font=labelfonts)
                lf.grid(row=row, column=column, padx=10, pady=5, ipadx=30, ipady=5, sticky='news')
                # Dictionary of buttons for toggling
                buttonDict = {}
                # Loop over buttons
                row = 0
                for vj in value:
                    name = vj['name']

                    if vj['type'] == 'checkbutton':
                        self.settings[name] = tk.BooleanVar()
                        buttons = []
                        toggleFunction = self.toggler(buttons, name)
                        if 'toggle' in vj:
                            button = ttk.Checkbutton(lf, text=vj['label'], variable=self.settings[name], command=toggleFunction, state=tk.DISABLED)
                        else:
                            button = ttk.Checkbutton(lf, text=vj['label'], variable=self.settings[name], command=toggleFunction)
                        button.grid(row=row, padx=10, sticky='we')
                        self.buildToolTip(button, vj)
                        buttonDict[name] = buttons
                        if 'toggle' in vj:
                            buttonDict[vj['toggle']].append((self.settings[vj['name']], button))
                        row += 1
                        if 'indent' in vj:
                            self.togglers.append(toggleFunction)
                            for vk in vj['indent']:
                                self.settings[vk['name']] = tk.BooleanVar()
                                button = ttk.Checkbutton(lf, text=vk['label'], variable=self.settings[vk['name']], state=tk.DISABLED)
                                button.grid(row=row, padx=30, sticky='w')
                                self.buildToolTip(button, vk)
                                buttons.append((self.settings[vk['name']], button))
                                if 'toggle' in vk:
                                    buttonDict[vk['toggle']].append((self.settings[vk['name']], button))
                                row += 1

                    elif vj['type'] == 'spinbox':
                        text = f"{vj['label']}:".ljust(20, ' ')
                        ttk.Label(lf, text=text).grid(row=row, column=0, padx=10, sticky='w')
                        spinbox = vj['spinbox']
                        self.settings[name] = tk.IntVar()
                        self.settings[name].set(spinbox['default'])
                        box = tk.Spinbox(lf, from_=spinbox['min'], to=spinbox['max'], width=3, textvariable=self.settings[name], state='readonly')
                        box.grid(row=row, column=1, padx=0, sticky='w')
                        self.buildToolTip(box, vj)
                        row += 1

                    elif vj['type'] == 'radiobutton':
                        self.settings[name] = tk.BooleanVar()
                        buttons = []
                        toggleFunction = self.toggler(buttons, name)
                        button = ttk.Checkbutton(lf, text=vj['label'], variable=self.settings[name], command=toggleFunction)
                        button.grid(row=row, padx=10, sticky='w')
                        self.buildToolTip(button, vj)
                        self.togglers.append(toggleFunction)
                        row += 1
                        keyoption = name+'-option'
                        self.settings[keyoption] = tk.StringVar()
                        self.settings[keyoption].set(None)
                        for ri in vj['indent']:
                            radio = tk.Radiobutton(lf, text=ri['label'], variable=self.settings[keyoption], value=ri['value'], padx=15, state=tk.DISABLED)
                            radio.grid(row=row, column=0, padx=14, sticky='w')
                            self.buildToolTip(radio, ri)
                            buttons.append((self.settings[keyoption], radio))
                            row += 1

        # For warnings/text at the bottom
        self.canvas = tk.Canvas()
        self.canvas.grid(row=6, column=0, columnspan=20, pady=10)

    # Ensures a correct path is selected.
    # Contained files are important for checking, so it will return a sorted list of paks too!
    def checkFile(self, path):
        dirs = path.split('/')
        if 'romfs' in dirs or 'RomFS' in dirs or 'Sunrise-E' in dirs or 'Paks' in dirs:
            fileNames = glob.glob(path + '/**/*.pak', recursive=True)
        else:
            return

        for fileName in fileNames:
            baseName = os.path.basename(fileName)
            if baseName == 'Sunrise-E-Switch.pak':
                self.settings['system'].set('Switch')
                return fileName
            if baseName == 'Bravely_Default_II-WindowsNoEditor.pak':
                self.settings['system'].set('Steam')
                return fileName

    def getPakFile(self):
        path = filedialog.askdirectory()
        if not path:
            return
        pakFile = self.checkFile(path)
        self.loadPakFile(pakFile)

    def loadPakFile(self, pakFile):
        self.clearBottomLabels()
        if pakFile:
            self.bottomLabel('Loading Pak....', 'blue', 0)
            try:
                if self.settings['system'].get() == 'Switch':
                    self.rom = ROM_SWITCH(pakFile)
                elif self.settings['system'].get() == 'Steam':
                    self.rom = ROM_PC(pakFile)
            except:
                self.clearBottomLabels()
                self.bottomLabel('Your game is incompatible with this randomizer.','red',0)
                self.bottomLabel('It has only been tested on Steam and Switch releases.','red',1)
            else:
                pakDir = os.path.dirname(pakFile)
                self.settings['rom'].set(pakDir)
                self.bottomLabel('Done', 'blue', 1)
        else:
            self.settings['rom'].set('')
            self.bottomLabel('The folder selected is invalid or does not contained the required paks.', 'red', 0)
            self.bottomLabel('e.g. ...Sunrise-E\Content\Paks', 'red', 2)

    def toggler(self, lst, key):
        def f():
            if self.settings[key].get():
                try: # "if radiobutton"
                    lst[0][1].select() # Selects the first option
                except (AttributeError, IndexError) as error:
                    pass
                for vi, bi in lst:
                    bi.config(state=tk.NORMAL)
            else:
                for vi, bi in lst:
                    if isinstance(vi.get(), bool):
                        vi.set(False)
                    if isinstance(vi.get(), str):
                        vi.set(None)
                    bi.config(state=tk.DISABLED)
            return key, lst
        return f

    def buildToolTip(self, button, field, wraplength=200):
        if isinstance(field, str):
            CreateToolTip(button, field, wraplength)
        if isinstance(field, dict):
            if 'help' in field:
                CreateToolTip(button, field['help'])

    def turnBoolsOff(self):
        for si in self.settings.values():
            if isinstance(si.get(), bool):
                si.set(False)
            
    def initialize_settings(self, settings):
        self.settings['release'].set(RELEASE)
        if settings is None:
            self.turnBoolsOff()
            return
        for key, value in settings.items():
            if key == 'rom':
                if not os.path.isdir(value):
                    continue
                pakFile = self.checkFile(value)
                if pakFile:
                    self.loadPakFile(pakFile)
            if key == 'release':
                continue
            if key not in self.settings:
                continue
            self.settings[key].set(value)
        for toggle in self.togglers:
            key, buttons = toggle()
            # Set the correct option for radio buttons
            if settings[key] and key+'-option' in settings:
                for option, button in buttons:
                    button.select()
                    if self.settings[key+'-option'] == settings[key+'-option']:
                        break

    def bottomLabel(self, text, fg, row):
        L = tk.Label(self.canvas, text=text, fg=fg)
        L.grid(row=row, columnspan=20)
        self.warnings.append(L)
        self.master.update()

    def clearBottomLabels(self):
        while self.warnings != []:
            warning = self.warnings.pop()
            warning.destroy()
        self.master.update()
        
    def randomSeed(self):
        self.settings['seed'].set(random.randint(0, 1e8))

    def randomize(self):
        if self.settings['rom'].get() == '':
            self.clearBottomLabels()
            self.bottomLabel('Must specify the path to your "Paks" folder', 'red', 0)
            return

        settings = { key: value.get() for key, value in self.settings.items() }

        self.clearBottomLabels()
        self.bottomLabel('Randomizing....', 'blue', 0)

        if randomize(self.rom, settings):
            self.clearBottomLabels()
            self.bottomLabel('Randomizing...done! Good luck!', 'blue', 0)
        else:
            self.clearBottomLabels()
            self.bottomLabel('Randomizing failed.', 'red', 0)


def randomize(rom, settings):
    try:
        # Start with a fresh ROM
        rom.clean()
        # Load data
        if settings['system'] == 'Steam':
            mod = STEAM(rom, settings)
        elif settings['system'] == 'Switch':
            mod = SWITCH(rom, settings)
        else:
            sys.exit(f"{settings['system']} not included in the randomizer!")
        # Modify data
        mod.randomize()
        mod.qualityOfLife()
        # Dump pak
        mod.dump()
        return True
    except:
        mod.failed()
        return False


if __name__ == '__main__':
    if len(sys.argv) > 2:
        print('Usage: python gui.py <settings.json>')
    elif len(sys.argv) == 2:
        with open(sys.argv[1], 'r') as file:
            settings = hjson.load(file)
        exePath = os.path.dirname(sys.argv[0])
        if exePath:
            os.chdir(exePath)
        GuiApplication(settings)
    else:
        GuiApplication()
