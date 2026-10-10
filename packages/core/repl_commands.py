"""Discoverable, fixed console commands; no shell or model dispatch."""
import difflib
import sys
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    usage: str
    description: str
    group: str
    arguments: str = 'none'


COMMANDS = {
    'help': Command('help [COMMAND]', 'Show all commands or help for one command.', 'Session', 'help'),
    'status': Command('status', 'Show the active context, selected scan and coverage.', 'Session'),
    'clear': Command('clear', 'Clear the terminal display; keep the session and saved results.', 'Session'),
    'doctor': Command('doctor', 'Check local prerequisites and setup.', 'Session'),
    'stop': Command('stop', 'Close the context and its services; retain saved results.', 'Session'),
    'quit': Command('quit', 'Exit and clean up owned processes.', 'Session'),
    'project': Command('project PATH', 'Select a source-only project; quote paths with spaces.', 'Project', 'path'),
    'init': Command('init', 'Select the launch directory for source-only analysis (project .).', 'Project'),
    'scan': Command('scan', 'Run source analysis on the selected project. Ctrl+C cancels.', 'Project'),
    'routes': Command('routes', 'List the selected project scan\'s routes.', 'Project'),
    'history': Command('history', 'List the ten latest saved project scans, newest first.', 'Project'),
    'use': Command('use NUMBER', 'Select a project scan from history.', 'Project', 'number'),
    'findings': Command('findings', 'List verdicts for the selected scan.', 'Evidence'),
    'inspect': Command('inspect NUMBER', 'Show a finding\'s source references and validation summary.', 'Evidence', 'number'),
    'report': Command('report [json]', 'Export a private Markdown or JSON report.', 'Evidence', 'report'),
    'demo': Command('demo [browser]', 'Authorize bounded checks of the bundled synthetic local demo.', 'Demo', 'demo'),
    'fix': Command('fix NUMBER', 'Explicitly approve a disposable demo patch; review still required.', 'Demo', 'number'),
}
ALIASES = {'1': 'demo', '2': 'doctor', '?': 'help', 'exit': 'quit', 'q': 'quit',
           'context': 'status', 'export': 'report'}


def canonical(value):
    name = value.removeprefix('/').casefold()
    return ALIASES.get(name, name)


def validate(command, arguments):
    kind = COMMANDS[command].arguments
    valid = {
        'none': not arguments,
        'path': len(arguments) == 1 and bool(arguments[0]),
        'number': len(arguments) == 1 and arguments[0].isascii() and arguments[0].isdigit()
                  and len(arguments[0]) <= 6 and int(arguments[0]) > 0,
        'help': len(arguments) <= 1,
        'demo': arguments in ([], ['browser']),
        'report': arguments in ([], ['json']),
    }[kind]
    return valid


def display(value, limit=1000):
    """Keep source names and analysis text from injecting terminal controls."""
    text = str(value)
    escaped = ''.join(f'\\u{ord(c):04x}' if ord(c) < 32 or 127 <= ord(c) < 160 or
                      '\u202a' <= c <= '\u202e' or '\u2066' <= c <= '\u2069' else c for c in text[:limit])
    return escaped + ('…' if len(text) > limit else '')


def show_help(output, topic=None):
    if topic:
        name = canonical(topic)
        if name not in COMMANDS:
            unknown(name, output)
            return
        spec = COMMANDS[name]
        output('/' + spec.usage + ' — ' + spec.description)
        if name == 'fix':
            output('Only supported demo findings can be patched. This command approves the experiment; review the diff before use.')
        if name in ('init', 'project', 'scan'):
            output('Source-only: no project scripts, installs, runtime requests, LLM calls or patches. Static findings are hypotheses.')
        return
    for group in ('Session', 'Project', 'Evidence', 'Demo'):
        output(group)
        for spec in COMMANDS.values():
            if spec.group == group:
                output('  /' + spec.usage + ' — ' + spec.description)
    output('Slash prefixes are optional. Aliases: /context → /status · /export → /report · /exit → /quit.')
    output('Tab completes commands; ↑/↓ recall input in this process only when terminal editing is available.')
    output('Choosing Demo authorizes bounded checks of the bundled synthetic local app.')
    output('fix NUMBER explicitly approves a disposable patch experiment; every patch needs review.')
    output('Project mode is source-only; it never builds, installs, executes or patches your project.')
    output('Ctrl+C during work cancels it; at the prompt it exits. /clear keeps results; /stop closes the context.')


def unknown(command, output):
    matches = difflib.get_close_matches(command, COMMANDS, n=1, cutoff=0.65)
    output('Unknown command: ' + display(command, 80) +
           ('. Did you mean /' + matches[0] + '?' if matches else '. Type /help for commands.'))
    output('Enter a listed command; natural-language requests and shell commands are not executed.')


def complete(text, state):
    # Command names only: never inspect a project or complete filesystem/secret values.
    prefix = '/' if text.startswith('/') else ''
    names = [*COMMANDS, *(name for name in ALIASES if name.isalpha() and len(name) > 1)]
    candidates = [prefix + name for name in names if name.startswith(text.removeprefix('/').casefold())]
    return candidates[state] if state < len(candidates) else None


@contextmanager
def terminal_input(enabled):
    """Optional standard-library editing. Never read/write a history file."""
    if not enabled:
        yield
        return
    try:
        import readline
    except ImportError:
        yield
        return
    previous = readline.get_completer()
    delimiters = readline.get_completer_delims()
    history_length = readline.get_history_length()
    history = [readline.get_history_item(i) for i in range(1, readline.get_current_history_length() + 1)]
    def command_completion(text, state):
        return complete(text, state) if readline.get_begidx() == 0 else None
    try:
        readline.clear_history()
        readline.set_history_length(100)
        readline.set_completer(command_completion)
        readline.set_completer_delims(' \t\n')
        readline.parse_and_bind('bind ^I rl_complete' if 'libedit' in (readline.__doc__ or '') else 'tab: complete')
        yield
    finally:
        readline.clear_history()
        for item in history:
            readline.add_history(item)
        readline.set_history_length(history_length)
        readline.set_completer(previous)
        readline.set_completer_delims(delimiters)


def interactive(input_fn):
    return input_fn is input and sys.stdin.isatty() and sys.stdout.isatty()
