from PyQt5 import QtCore
import os, json

class ScoreboardHelper(QtCore.QObject):
    _cmd_prefix = '!sh'

    
    def __init__(self, logger, core, config_file):
        super(ScoreboardHelper, self).__init__(core)
        self.logger = logger

        # load config
        self.configs = {}
        if os.path.exists(config_file):
            self.logger.info('Loading configs...')
            with open(config_file, 'r', encoding='utf-8') as cf:
                self.configs = json.load(cf)
        else:
            self.logger.warning('config.json not found. Using default settings.')

        