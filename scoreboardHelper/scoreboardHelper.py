from PyQt5 import QtCore
import os, json

class ScoreboardHelper(QtCore.QObject):
    _cmd_prefix = '!sb'

    
    def __init__(self, logger, core, config_file):
        super(ScoreboardHelper, self).__init__(core) 
        self.logger = logger
        self.core = core

        # load config
        self.configs = {}
        if os.path.exists(config_file):
            self.logger.info('Loading configs...')
            with open(config_file, 'r', encoding='utf-8') as cf:
                self.configs = json.load(cf)
        else:
            self.logger.warning('config.json not found. Using default settings.')
            self.configs = {
                "visible_scoreboards": [],
                "cycle_enabled": True,
                "cycle_scoreboards": [],
                "sec_between_cycle": 15,
                "sec_view_stay": 3
            }
            json.dump(self.configs, open(config_file, 'w', encoding='utf-8'), indent=2)

        self.cycle_enabled = self.configs.get('cycle_enabled', True)

        # load mcBasicLib
        self.utils = core.get_plugin('mcBasicLib')
        if self.utils is None:
            self.logger.error('Failed to load plugin mcBasicLib. ScoreboardHelper will be disabled.')
            self.logger.error('Please make sure that mcBasicLib has been added to plugins.')
            return      # self.disabled = True

        # connect signals and slots
        self.utils.sig_input.connect(self.on_player_input)

        # available commands
        self.cmd_list = {
            'help': self.help,
            'list': self.list_visible_sb,
            'view': self.view_sb,
            'add': self.add_sb,
            'rm': self.rm_sb,
            'cycle': self.set_cycle,
            'settime': self.set_time,
        }


    def unknown_command(self, player):
        self.logger.warning('Unknown command sent by player {}.'.format(player.name))
        self.utils.tell(player, 'Unknown command. Type "!sb help" for help.')


    @QtCore.pyqtSlot(tuple)
    def on_player_input(self, pair):
        self.logger.debug(f'{self.__class__.__name__}.on_player_input() called')
        player, text = pair
        text_list = text.strip().split()
        
        if len(text_list) and text_list[0] == self._cmd_prefix:
            if len(text_list) > 1 and text_list[1] in self.cmd_list:
                self.cmd_list[text_list[1]](player, text_list[2:])
            else:
                self.unknown_command(player)

    
    # Plugin Functions
    def help(self, player, args: list):
        if len(args):
            self.unknown_command(player)
            return

        help_info = '''\
------------------ ScoreboardHelper Command List ------------------
"!sb help": Show this help message.
"!sb list": List all scoreboards.
"!sb view <name>": View a certain scoreboard for a period of time.
-------------------------------------------------------------------'''
        op_help_info = '''\
----------------- ScoreboardHelper OP Command List ----------------
"!sb cycle <true|false>": Turn on/off scoreboard cycling.
"!sb <add|rm> <visible|cycle> <name>": 
    Add/remove a scoreboard from visible/cycle list.
"!sb settime <visible|cycle> <time_in_sec>":
    Set cycle interval / view duration time in sec.
-------------------------------------------------------------------'''
        help_msg = help_info + (op_help_info if player.is_op() else '')
        self.utils.tell(player, help_msg)


    def list_visible_sb(self, player, args: list):
        if len(args):
            self.unknown_command(player)
            return

        if player.is_op():
            self.utils.tell(player, 'Scoreboards cycling:', bold=True)
            msg = '\t' + '\n\t'.join(self.configs.get('cycle_scoreboards', []))
            self.utils.tell(player, msg)
            self.utils.tell(player, 'Scoreboards visible to players:', bold=True)
        else:
            self.utils.tell(player, 'Scoreboards available:', bold=True)
        msg = '\t' + '\n\t'.join(self.configs.get('visible_scoreboards', []))
        self.utils.tell(player, msg)


    def view_sb(self, player, args: list):
        if len(args) != 1:
            self.unknown_command(player)
            return

        sb_name = args[0]
        if sb_name not in self.configs.get('visible_scoreboards', []):
            self.utils.tell(player, f'Invalid scoreboard \'{sb_name}\'. Use \'!sb list\' to see available scoreboards.')
            return
        
        self.cycle_enabled = False
        self.core.write_server(f'/scoreboard objectives setdisplay sidebar {sb_name}')
        interval = self.configs.get('sec_view_stay', 3) * 1000
        self.view_timer = QtCore.QTimer()
        self.view_timer.singleShot(interval, self.view_timer_end)
    
    def view_timer_end(self):
        self.cycle_enabled = True


    def add_sb(self, player, args: list):
        pass


    def rm_sb(self, player, args: list):
        pass


    def set_cycle(self, player, args: list):
        pass


    def set_time(self, player, args: list):
        pass