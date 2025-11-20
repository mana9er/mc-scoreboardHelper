from PyQt5 import QtCore
import os, json

class ScoreboardHelper(QtCore.QObject):
    _cmd_prefix = '!sb'
    _default_cycle_interval = 600
    _default_view_stay = 5

    
    def __init__(self, logger, core, config_file):
        super(ScoreboardHelper, self).__init__(core) 
        self.logger = logger
        self.core = core
        self.config_file = config_file

        # load config
        self.configs = {}
        if os.path.exists(self.config_file):
            self.logger.info('Loading configs...')
            with open(self.config_file, 'r', encoding='utf-8') as cf:
                self.configs = json.load(cf)
            self.logger.info('Configs loaded.')
        else:
            self.logger.warning('config.json not found. Using default settings.')
            self.configs = {
                "visible_scoreboards": [],
                "cycle_enabled": True,
                "cycle_scoreboards": [],
                "sec_between_cycle": self._default_cycle_interval,
                "sec_view_stay": self._default_view_stay
            }
            self.update_config_json()

        # load mcBasicLib
        self.utils = core.get_plugin('mcBasicLib')
        if self.utils is None:
            self.logger.error('Failed to load plugin mcBasicLib. ScoreboardHelper will be disabled.')
            self.logger.error('Please make sure that mcBasicLib has been added to plugins.')
            return      # self.disabled = True

        # initialize cycle timer
        self.cycle_enabled = self.configs.get('cycle_enabled', True)
        self.cycle_index = 0
        self.cycle_timer = QtCore.QTimer(self)
        self.cycle_timer.timeout.connect(self.cycle_timer_action)   # type: ignore[attr-defined]
        self.std_cyc_interval_ms = self.configs.get('sec_between_cycle', self._default_cycle_interval) * 1000    # msec
        self.cycle_timer.start(self.std_cyc_interval_ms)      # start cycle timer
        self._cycle_remaining_ms = 0   # msec

        # connect signals and slots
        self.utils.sig_input.connect(self.on_player_input)

        # available commands
        self.cmd_list = {
            'help': self.help,
            'list': self.list_visible_sb,
            'view': self.view_sb,
            'skip': self.skip_sb,
            'add': self.add_sb,
            'remove': self.rm_sb,
            'rm': self.rm_sb,
            'cycle': self.set_cycle,
            'settime': self.set_time,
        }


    def unknown_command(self, player):
        self.logger.warning('Unknown command sent by player {}.'.format(player.name))
        self.utils.tell(player, f'Unknown command. Type "{self._cmd_prefix} help" for help.')


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


    def update_config_json(self):
        json.dump(self.configs, open(self.config_file, 'w', encoding='utf-8'), indent=4)


    ## Timer-triggered Functions
    def cycle_timer_action(self, forced = False):
        if self.cycle_enabled or forced:
            # Restore standard interval if it was changed (e.g. by resuming from view)
            if self.cycle_timer.interval() != self.std_cyc_interval_ms:
                self.cycle_timer.setInterval(self.std_cyc_interval_ms)

            cycle_sb_list = self.configs.get('cycle_scoreboards', [])
            if len(cycle_sb_list) <= 0:
                self.logger.debug('No scoreboards to cycle. Skipping.')
                # TODO: disable cycle on empty list, and re-enable on '!sb add'
            else:
                self.cycle_index %= len(cycle_sb_list)
                self.core.write_server(f'/scoreboard objectives setdisplay sidebar {cycle_sb_list[self.cycle_index]}')
                self.cycle_index += 1

    def view_timer_end(self):
        self.cycle_index -= 1   # return to previous showing scoreboard
        self.cycle_timer_action(forced=True)
        
        # Resume cycle timer with remaining time if available and cycle enabled
        if self.cycle_enabled:
            if self._cycle_remaining_ms > 0:
                self.cycle_timer.start(self._cycle_remaining_ms)
                self._cycle_remaining_ms = 0 # Reset instead of delete to avoid attribute error
            else:
                self.cycle_timer.start()

    
    ## Plugin Command Functions
    def help(self, player, args: list):
        if len(args):
            self.unknown_command(player)
            return

        help_info = f'''\
------------ ScoreboardHelper Command List ------------
"{self._cmd_prefix} help": Show this help message.
"{self._cmd_prefix} list": List all scoreboards.
"{self._cmd_prefix} view <name>": View a certain scoreboard for a period of time.
"{self._cmd_prefix} skip": Skip the displaying scoreboard.
----------------------------------------------------'''
        op_help_info = f'''
----------- ScoreboardHelper OP Command List ----------
"{self._cmd_prefix} cycle <true | t | false | f>": Turn on / off scoreboard cycling.
"{self._cmd_prefix} <add | remove | rm> <visible | cycle> <name>": 
    Add / remove a scoreboard from visible / cycle list.
"{self._cmd_prefix} settime <view | cycle> <second>":
    Set cycle interval / view duration time in second.
----------------------------------------------------'''
        help_msg = help_info + (op_help_info if player.is_op() else '')
        self.utils.tell(player, help_msg)


    def list_visible_sb(self, player, args: list):
        if len(args):
            self.unknown_command(player)
            return

        if player.is_op():
            cycle_status_msg = f'enabled, interval {self.configs["sec_between_cycle"]}s' if self.cycle_enabled else 'disabled'
            self.utils.tell(player, f'Scoreboards cycling ({cycle_status_msg}):')
            msg = '    ' + '\n    '.join(self.configs.get('cycle_scoreboards', []))
            self.utils.tell(player, msg)
            self.utils.tell(player, f'Scoreboards visible to players (stay {self.configs["sec_view_stay"]}s):')
        else:
            self.utils.tell(player, 'Scoreboards available:')
        msg = '    ' + '\n    '.join(self.configs.get('visible_scoreboards', []))
        self.utils.tell(player, msg)


    def view_sb(self, player, args: list):
        if len(args) != 1:
            self.unknown_command(player)
            return

        sb_name = args[0]
        if not player.is_op() and sb_name not in self.configs.get('visible_scoreboards', []):   # op can override the visible list
            self.utils.tell(player, f'Invalid scoreboard \'{sb_name}\'. Use \'{self._cmd_prefix} list\' to see available scoreboards.')
            return
        
        # Save remaining time if cycle timer is active
        if self.cycle_enabled:
            self._cycle_remaining_ms = self.cycle_timer.remainingTime()
            self.logger.debug(f'view_sb(): cycle enabled. Remaining time saved: {self._cycle_remaining_ms} ms.')
            self.cycle_timer.stop()

        self.core.write_server(f'/scoreboard objectives setdisplay sidebar {sb_name}')
        view_interval = self.configs.get('sec_view_stay', self._default_view_stay)  # sec
        self.utils.tell(player, f'Viewing \'{sb_name}\' for {view_interval} seconds.')
        self.view_timer = QtCore.QTimer(self)
        self.view_timer.timeout.connect(self.view_timer_end)  # type: ignore[attr-defined]
        self.view_timer.setSingleShot(True)
        self.view_timer.start(view_interval * 1000)


    def skip_sb(self, player, args: list):
        if len(args):
            self.unknown_command(player)
            return
        
        if hasattr(self, 'view_timer') and self.view_timer.isActive():  # player is viewing a selected scoreboard
            self.logger.debug('skip_sb(): view timer is active.')
            self.view_timer.stop()
            self.view_timer_end()
        else:   # TODO: permission control?
            self.logger.debug('skip_sb(): view timer is inactive.')
            self.cycle_timer_action(forced=True)
            if self.cycle_enabled:
                self.cycle_timer.start(self.std_cyc_interval_ms)
        
        self.utils.tell(player, f'Skipped displaying scoreborad.')



    def add_sb(self, player, args: list):
        if not player.is_op() or len(args) != 2:
            self.unknown_command(player)
            return
            
        sb_name = args[1]
        if args[0] == 'visible':
            if sb_name not in self.configs.get('visible_scoreboards', []):
                try:
                    self.configs['visible_scoreboards'].append(sb_name)
                except KeyError:
                    self.configs['visible_scoreboards'] = [sb_name]
                    self.logger.warning('Configuration \'visible_scoreboards\' not exist, creating a new list.')
                finally:
                    self.utils.tell(player, f'Added {sb_name} to visible scoreboards.')
                    self.update_config_json()
            else:
                self.utils.tell(player, f'Failed. Scoreboard \'{sb_name}\' is already in the list.')
        elif args[0] == 'cycle':
            if sb_name not in self.configs.get('cycle_scoreboards', []):
                try:
                    self.configs['cycle_scoreboards'].append(sb_name)
                except KeyError:
                    self.configs['cycle_scoreboards'] = [sb_name]
                    self.logger.warning('Configuration \'cycle_scoreboards\' not exist, creating a new list.')
                finally:
                    self.utils.tell(player, f'Added {sb_name} to cycling scoreboards.')
                    self.update_config_json()
            else:
                self.utils.tell(player, f'Failed. Scoreboard \'{sb_name}\' is already in the list.')
        else:
            self.unknown_command(player)


    def rm_sb(self, player, args: list):
        if not player.is_op() or len(args) != 2:
            self.unknown_command(player)
            return
            
        sb_name = args[1]
        if args[0] == 'visible':
            try:
                self.configs['visible_scoreboards'].remove(sb_name)
                self.utils.tell(player, f'Removed {sb_name} from visible scoreboards.')
                self.update_config_json()
            except:     # ValueError (name not in list) or KeyError (list not exist)
                self.utils.tell(player, f'Failed. Scoreboard \'{sb_name}\' not in the list!')
        elif args[0] == 'cycle':
            try:
                self.configs['cycle_scoreboards'].remove(sb_name)
                self.utils.tell(player, f'Removed {sb_name} from cycling scoreboards.')
                self.update_config_json()
            except:
                self.utils.tell(player, f'Failed. Scoreboard \'{sb_name}\' not in the list!')
        else:
            self.unknown_command(player)


    def set_cycle(self, player, args: list):
        cmd = args[0].lower()
        accept_cmd = ['true', 't', 'false', 'f']
        if not player.is_op() or len(args) != 1 or cmd not in accept_cmd:
            self.unknown_command(player)
            return

        if cmd == 'true' or cmd == 't':
            self.cycle_enabled = True
            self.cycle_timer.start() 
        else:
            self.cycle_enabled = False
            self.cycle_timer.stop()   
        self.configs['cycle_enabled'] = self.cycle_enabled
        self.utils.tell(player, f'Scoreboard cycling now set to {self.cycle_enabled}.')
        self.update_config_json()
        

    def set_time(self, player, args: list):
        if not player.is_op() or len(args) != 2:
            self.unknown_command(player)
            return

        try:
            sec = int(args[1])
            if sec < 1: raise ValueError('Interval too short')
        except:     # ValueError
            self.utils.tell(player, 'Invalid input. Please enter an integer (>= 1) for the new interval.')
            return
        
        if args[0] == 'view':
            self.configs['sec_view_stay'] = sec
            self.utils.tell(player, f'Set view stay to {sec}s.')
        elif args[0] == 'cycle':
            self.configs['sec_between_cycle'] = sec
            self.std_cyc_interval_ms = sec * 1000
            self.cycle_timer.start(self.std_cyc_interval_ms)
            self.utils.tell(player, f'Set cycle interval to {sec}s.')
        else:
            self.unknown_command(player)
            return
        self.update_config_json()