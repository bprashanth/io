"""Talk through Start here > Teams without the app: the real router (lib/modes.py) and lib/teams.py, with the tools
faked. Each step of a script is a click (an option's label) or something typed.

  python tests/teams_sim.py            run the scripted people below and print what Idli says
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import modes, teams  # noqa: E402

TOOLS = [{'name': 'mcp__cowork__' + n, 'input_schema': {}} for n in ('team_page', 'team_check', 'team_create')]


class Chat:
    def __init__(self, taken=()):
        self.messages = [{'role': 'user', 'content': [{'type': 'text', 'text': teams.TEAMS_CHAT}]}]
        self.n = 0
        self.taken = {t.lower() for t in taken}
        self.shown = []
        self.card = None
        self.created = None
        self.run()

    def run(self):
        """Ask the router until it waits for the person."""
        for _ in range(8):
            reply = modes.teams_chat_route({'model': 'idli-9b', 'tools': TOOLS, 'messages': self.messages})
            content = reply['content']
            self.messages.append({'role': 'assistant', 'content': content})
            uses = [b for b in content if b['type'] == 'tool_use']
            for b in content:
                if b['type'] == 'text':
                    self.shown.append(('idli', b['text']))
            if not uses:
                self.card = None
                return
            use = uses[0]
            name = use['name'].split('__')[-1]
            if name == 'AskUserQuestion':
                q = use['input']['questions'][0]
                self.card = (use['id'], q)
                self.shown.append(('card', q['question'] + '  [' + ' | '.join(o['label'] for o in q['options']) + ']'))
                return
            result = self.tool(name, use['input'])
            self.messages.append({'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': use['id'],
                                                               'content': json.dumps(result)}]})
        raise RuntimeError('the router did not stop')

    def tool(self, name, args):
        if name == 'team_page':
            return {'reply': '[Teams](http://dashboard.localhost:8797/teams?t=x&embed=1&h=96)'}
        if name == 'team_check':
            n = teams._clean_name(args['name'])
            if not n or n.lower() in self.taken or n.lower() in teams.RESERVED:
                return {'ok': False, 'error': f'There is already a {n} in your sidebar. Pick another name.'}
            return {'ok': True, 'name': n}
        if name == 'team_create':
            self.created = args
            self.shown.append(('setup', json.dumps(args)))
            return {'ok': True, 'name': args['name'], 'folder': '/x/teams/' + teams.slug(args['name'])}
        raise ValueError(name)

    def do(self, action):
        """Click an option of the open card (exact label), or type (into the card's box when one is open)."""
        self.n += 1
        if action.startswith('!') and self.card:
            return self.typed_over_card(action[1:])
        if self.card:
            tid, q = self.card
            self.shown.append(('you', action))
            text = f'User has answered your questions: "{q["question"]}"="{action}". You can now continue.'
            self.messages.append({'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tid,
                                                               'content': text}]})
        else:
            self.shown.append(('you', action))
            self.messages.append({'role': 'user', 'content': [{'type': 'text', 'text': action}]})
        self.card = None
        self.run()
        return self

    def typed_over_card(self, text):
        """Typed in the chat box while a card is open: Claude Code answers the card as dismissed."""
        tid, q = self.card
        self.messages.append({'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tid, 'is_error': True,
                                                           'content': "The user doesn't want to proceed with this tool use."}]})
        self.card = None
        self.messages.append({'role': 'user', 'content': [{'type': 'text', 'text': text}]})
        self.shown.append(('you', text))
        self.run()
        return self

    def transcript(self):
        return '\n'.join(f'{who:>5}: {text}' for who, text in self.shown)


SCRIPTS = {
    'straight': ['Make a team', 'Insights', 'Help women\'s groups around Ramtekdi get out of debt', 'Google Drive',
                 'A few of us', 'Yes', 'Yes, ask me each time', 'Set it up'],
    'it-tester': ['Make a team', "I'm from the IT team, just testing this for our programme people",
                  'Insights', "no idea, I'm not on that team", 'Use an example',
                  'mostly excel on my laptop', 'my team will use this from next week but I am just testing it now',
                  'not sure', 'no', 'Set it up'],
    'solo': ['Make a team', 'we are called the M&E team', 'track attendance in 40 schools', 'drive',
             'I am the single person in this team', 'yes names and phone numbers', 'sure, if it asks first',
             'Change something', 'Name', 'Field M&E', 'Set it up'],
    'questions': ['Make a team', 'what is a team?', 'Drivey', 'Insights', 'how long does this take?',
                  'reduce debt', 'kobo', 'just me', 'yes', 'ok', 'yes'],
    'stop-restart': ['Make a team', 'Insights', 'cancel', 'Make a team', 'Health', 'start over', 'Health',
                     'Better clinic follow-up', 'Google Drive', 'The whole team', 'No', 'No', 'looks good'],
    'odd-names': ['Make a team', 'yes', 'Team Insights', 'Help farmers sell at fair prices',
                  '!both, drive and some on my computer', 'what does outside service mean?', 'A few of us',
                  'Yes', 'what is the outside service?', 'No', 'Set it up'],
    'ramble': ['Make a team', 'hello', 'okay so basically we are a small livelihoods programme in Wardha and we '
               'want to call this Livelihoods Wardha', 'we want women to earn more from goats and poultry',
               'Somewhere else', 'just me for now, maybe two more later', 'Not sure', '!yes', 'Change something',
               'Goal', 'More income for 300 women from goats', 'go ahead'],
    'hindi-ish': ['Make a team', 'हमारी टीम का नाम Shiksha है', 'bacchon ki padhai behtar karna', 'Google Drive',
                  'poori team', 'haan', 'nahi', 'Set it up'],
    'garbage': ['Make a team', '???', 'asdf', 'Insights', '', 'Google Drive', 'banana', 'Just me', 'Yes', 'No',
                'hmm', 'Set it up'],
}


if __name__ == '__main__':
    names = sys.argv[1:] or list(SCRIPTS)
    for name in names:
        chat = Chat(taken=['Drivey'])
        for step in SCRIPTS[name]:
            chat.do(step)
        print(f'===== {name}\n{chat.transcript()}\n')
