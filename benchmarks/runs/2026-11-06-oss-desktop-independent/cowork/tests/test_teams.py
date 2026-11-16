"""Start here > Teams (lib/teams.py): the conversation through the real router, and the setup on disk.
The local 9B is switched off here (a dead address), so these test the rules it falls back to."""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'tests'))


@pytest.fixture(autouse=True)
def no_nine(monkeypatch):
    monkeypatch.setenv('IDLI_9B_URL', 'http://127.0.0.1:9')
    monkeypatch.setenv('IDLI_TEAMS_9B_TIMEOUT', '0.2')
    from lib import teams
    for f in (teams.read_name, teams.read_goal, teams.read_choice):
        f.cache_clear()


def run(steps, taken=('Drivey',)):
    from teams_sim import Chat
    chat = Chat(taken=taken)
    for s in steps:
        chat.do(s)
    return chat


def said(chat):
    return [t for who, t in chat.shown if who in ('idli', 'card')]


def test_opens_with_the_button_only():
    chat = run([])
    assert said(chat) == ['[Teams](http://dashboard.localhost:8797/teams?t=x&embed=1&h=96)']


def test_straight_through_makes_insights():
    chat = run(['Make a team', 'Insights', 'Lower household debt', 'Google Drive', 'A few of us', 'Yes',
                'Yes, ask me each time', 'Set it up'])
    assert chat.created['name'] == 'Insights' and chat.created['outside'] is True
    assert chat.created['goal'] == 'Lower household debt'
    last = said(chat)[-1]
    assert 'Insights is ready' in last and 'New chat' in last
    plan = next(t for t in said(chat) if t.startswith('**Insights**'))
    assert 'codes' in plan and 'outside service only if you say yes' in plan
    assert not any(ch in ' '.join(said(chat)) for ch in '→·')


def test_tester_from_it_gets_help_not_a_dead_end():
    chat = run(['Make a team', "I'm from the IT team, just testing this for the programme people"])
    assert said(chat)[-1].startswith('No problem. What should we call the team?')
    chat.do('Insights').do("no idea, I'm not on that team")
    assert said(chat)[-1].startswith('No problem. Use an example goal')
    chat.do('Use an example').do('Google Drive').do('my team will use it from next week, I am testing now')
    assert any('others can join when they are ready' in t for t in said(chat))
    chat.do('Not sure').do('No').do('Set it up')
    assert chat.created['trying'] is True and chat.created['goal'] == 'Lower household debt in 12 villages'
    assert chat.created['outside'] is False


def test_single_person_and_typed_answers():
    chat = run(['Make a team', 'call it Field M&E', 'attendance in 40 schools', 'drive',
                'I am the single person in this team', 'yes names and phone numbers', 'no thanks never',
                'looks good'])
    assert chat.created['name'] == 'Field M&E' and chat.created['people'] == 'Just me'
    assert chat.created['private'] == 'Yes' and chat.created['outside'] is False


def test_taken_and_reserved_names_ask_again():
    chat = run(['Make a team', 'Drivey'])
    assert 'already' in said(chat)[-1]
    chat = run(['Make a team', 'Health'], taken=('Health',))
    assert 'already' in said(chat)[-1]
    chat.do('Health Two')
    assert said(chat)[-1] == 'What does Health Two work towards? One line is enough.'


def test_greetings_are_not_names():
    chat = run(['Make a team', 'hello'])
    assert said(chat)[-1].startswith('What should we call the team?')


def test_questions_get_answers_then_the_same_question():
    chat = run(['Make a team', 'what is a team?'])
    assert said(chat)[-1].startswith('A team is a heading') and said(chat)[-1].endswith("What's your team called?")
    chat = run(['Make a team', 'Insights', 'debt', 'Google Drive', 'Just me', 'Yes', 'what is the outside service?'])
    assert said(chat)[-2].startswith('A service online') and said(chat)[-1].startswith("When a Mini can't")
    chat = run(['Make a team', 'Insights', 'ok'])
    assert said(chat)[-1].startswith('Use an example goal')


def test_cancel_and_start_again():
    chat = run(['Make a team', 'Insights', 'cancel'])
    assert said(chat)[-1].startswith('OK. Nothing was set up.')
    chat.do('Make a team')
    assert said(chat)[-1] == "What's your team called?"


def test_change_the_name_before_setup():
    chat = run(['Make a team', 'Insights', 'debt', 'Google Drive', 'Just me', 'Yes', 'No', 'Change something',
                'Name', 'Insights Wardha', 'Set it up'])
    assert chat.created['name'] == 'Insights Wardha'


def test_typing_while_a_card_is_open_answers_it():
    chat = run(['Make a team', 'Insights', 'debt', '!it is all in google sheets'])
    assert said(chat)[-1].startswith('Who will use Insights?')


def test_not_drive_is_noted_but_continues():
    chat = run(['Make a team', 'Insights', 'debt', 'kobo'])
    assert any('reads files from Google Drive for now' in t for t in said(chat))


def test_setup_makes_the_folder_and_heading(tmp_path, monkeypatch):
    from lib import teams
    monkeypatch.setenv('IDLI_HOME', str(tmp_path))
    projects = []
    calls = []

    def fake(*args, parse=True):
        calls.append(args)
        if args[:2] == ('project', 'ls'):
            return projects
        if args[:2] == ('project', 'create'):
            projects.append({'projectId': 'p1', 'path': args[2], 'name': os.path.basename(args[2])})
            return ''
        if args[:2] == ('project', 'rename'):
            projects[0]['name'] = args[3]
            return ''
        raise AssertionError(args)
    monkeypatch.setattr(teams, '_paseo', fake)
    out = teams.create({'name': 'Insights', 'goal': 'Debt', 'outside': False}, HERE)
    folder = tmp_path / 'teams' / 'insights'
    assert out == {'ok': True, 'name': 'Insights', 'folder': str(folder)}
    assert json.loads((folder / 'team.json').read_text())['name'] == 'Insights'
    assert (folder / 'cowork.tools').read_text().split() == teams.TEAM_TOOLS
    assert (folder / 'CLAUDE.md').read_text() == open(os.path.join(HERE, 'idli', 'CLAUDE.md')).read()
    assert (folder / 'no-query-service').exists()
    assert projects[0]['name'] == 'Insights'
    assert teams.team_dir(str(folder)) == str(folder.resolve())
    assert teams.team_dir(str(tmp_path / 'cowork-real')) is None
    again = teams.create({'name': 'Insights'}, HERE)  # safe to rerun for the same team
    assert again['ok'] and len([c for c in calls if c[:2] == ('project', 'create')]) == 1
    assert teams.check('Insights', projects)['ok'] is False


def test_team_tools_match_drivey():
    import importlib.util
    spec = importlib.util.spec_from_file_location('boot', os.path.join(HERE, 'desktop', 'idli-bootstrap.py'))
    boot = importlib.util.module_from_spec(spec)
    sys.argv, old = ['x', '--dry-run'], sys.argv
    try:
        spec.loader.exec_module(boot)
    finally:
        sys.argv = old
    from lib import teams
    assert boot.TOOLSETS['Drivey'] == teams.TEAM_TOOLS
    assert {'team_page', 'team_check', 'team_create'} <= set(boot.TOOLSETS['Start here'])
    assert boot.TEAMS == teams.TEAMS_CHAT


def test_team_work_folder_is_beside_drivey(tmp_path, monkeypatch):
    from lib import home, teams
    monkeypatch.setenv('IDLI_HOME', str(tmp_path))
    monkeypatch.delenv('IDLI_CLAUDE_WORK', raising=False)
    folder = tmp_path / 'teams' / 'insights'
    folder.mkdir(parents=True)
    (folder / 'team.json').write_text('{"name": "Insights"}')
    assert str(home.work_dir(str(folder))) == str((tmp_path / 'claude-masked-insights').resolve())
    assert home.work_dir(str(tmp_path / 'cowork-real')).name == 'claude-masked'


def test_spoken_lead_ins_are_dropped_from_the_goal():
    from lib import teams
    assert teams.read_goal("ok so: actually it's helping women's groups get out of debt")['goal'] == \
        "Helping women's groups get out of debt"
    assert teams.read_goal('we help 300 farmers sell at fair prices')['goal'] == 'Help 300 farmers sell at fair prices'


def test_page_reads_names_and_goals():
    from lib import teams
    assert teams.name_from('call it Field M&E', )['name'] == 'Field M&E'
    assert teams.name_from('Drivey')['ok'] is False
    assert teams.name_from('hello')['ok'] is False
    assert teams.goal_from("ok so we help women's groups get out of debt") == "Help women's groups get out of debt"


def test_page_lists_and_deletes_teams(tmp_path, monkeypatch):
    from lib import teams
    monkeypatch.setenv('IDLI_HOME', str(tmp_path))
    (tmp_path / 'cowork-real').mkdir()
    projects = [{'projectId': 'pd', 'path': str(tmp_path / 'cowork-real'), 'name': 'Drivey'}]
    calls = []

    def fake(*args, parse=True):
        calls.append(args)
        if args[:2] == ('project', 'ls'):
            return projects
        if args[:2] == ('project', 'create'):
            projects.append({'projectId': 'p1', 'path': args[2], 'name': os.path.basename(args[2])})
        if args[:2] == ('project', 'rename'):
            projects[-1]['name'] = args[3]
        if args[:2] == ('project', 'delete'):
            projects[:] = [p for p in projects if p['projectId'] != args[2]]
        if args[:1] == ('ls',):
            return [{'id': 'a1', 'cwd': str(tmp_path / 'teams' / 'insights'), 'name': 'x'}]
        return ''
    monkeypatch.setattr(teams, '_paseo', fake)
    teams.create({'name': 'Insights', 'goal': 'Debt', 'outside': True}, HERE)
    (tmp_path / 'claude-masked-insights').mkdir()
    cards = teams.list_teams()['teams']
    assert [c['id'] for c in cards] == ['drivey', 'insights'] and cards[1]['ready'] and cards[0]['builtin']
    assert teams.delete_team('drivey')['ok'] is False
    assert teams.delete_team('../etc')['ok'] is False
    assert teams.delete_team('insights') == {'ok': True}
    assert ('delete', 'a1') in calls and ('project', 'delete', 'p1') in calls
    assert not (tmp_path / 'teams' / 'insights').exists() and not (tmp_path / 'claude-masked-insights').exists()
    assert len(list((tmp_path / 'archive' / 'teams').iterdir())) == 2
    assert [c['id'] for c in teams.list_teams()['teams']] == ['drivey']
