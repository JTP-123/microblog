import os, click 

def register(app):
    @app.cli.group() # commands can be attached to such command of type group()
    def translate():
        """Translation and localization commands.""" # comment docstring used as -help output under group command
        pass 

    @translate.command() # subcommand of group() command translate
    def update():
        """Update all languages.""" # comment docstring used as -help output under group command
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'): # system函数正常执行subshell command会返回0, 否则返回1
            raise RuntimeError('extract command failed')
        if os.system('pybabel update -i messages.pot -d app/translations'):
            raise RuntimeError('update command failed')
        os.remove('messages.pot')

    @translate.command()
    def compile():
        """Compile all languages.""" # comment docstring used as -help output under group command
        if os.system('pybabel compile -d app/translations'):
            raise RuntimeError('compile command failed')

    @translate.command()
    @click.argument('lang')
    def init(lang):
        """Initialize a new language."""
        if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
            raise RuntimeError('extract command failed')
        if os.system('pybabel init -i messages.pot -d app/translations -l ' + lang):
            raise RuntimeError('init command failed')
        os.remove('messages.pot')


