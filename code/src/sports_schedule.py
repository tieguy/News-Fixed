#!/usr/bin/env python3
"""Parse Duke basketball schedules from ICS files."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from icalendar import Calendar
import pytz


class DukeBasketballSchedule:
    """Parse and query Duke basketball schedules."""

    def __init__(self, data_dir: Path = None):
        """
        Initialize the schedule parser.

        Args:
            data_dir: Path to data directory (defaults to ../data)
        """
        if data_dir is None:
            # Navigate from code/src/ to project root, then to data/
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = data_dir
        self.sports_dir = data_dir / "sports"

    def parse_ics_file(self, ics_path: Path) -> List[Dict]:
        """
        Parse an ICS file and return list of events.

        Args:
            ics_path: Path to ICS file

        Returns:
            List of event dicts with 'date', 'time', 'opponent', 'location',
            'home_away', 'tv', 'result'
        """
        events = []

        with open(ics_path, 'rb') as f:
            cal = Calendar.from_ical(f.read())

        for component in cal.walk('VEVENT'):
            # Get start time (convert to local Pacific time)
            dtstart = component.get('dtstart').dt
            if isinstance(dtstart, datetime):
                # Convert to Pacific Time
                pacific = pytz.timezone('US/Pacific')
                if dtstart.tzinfo is None:
                    dtstart = pytz.utc.localize(dtstart)
                dtstart = dtstart.astimezone(pacific)

            # Parse summary for opponent and result
            summary = str(component.get('summary', ''))
            description = str(component.get('description', ''))
            location = str(component.get('location', ''))

            # Determine home/away and opponent
            home_away = 'Home'
            opponent = ''
            result = None

            if ' vs ' in summary:
                home_away = 'Home'
                opponent = summary.split(' vs ')[1].split('-')[0].strip()
            elif ' at ' in summary:
                home_away = 'Away'
                opponent = summary.split(' at ')[1].strip()

            # Check for result (Win/Loss with score)
            if '[W]' in summary or '\nW ' in description:
                # Extract score from description if available
                for line in description.split('\n'):
                    if line.startswith('W ') or line.startswith('L '):
                        result = line.strip()
                        break

            # Extract TV info
            tv = None
            if 'TV:' in description:
                for line in description.split('\n'):
                    if line.startswith('TV:'):
                        tv = line.replace('TV:', '').strip()
                        break

            events.append({
                'date': dtstart.date() if isinstance(dtstart, datetime) else dtstart,
                'time': dtstart.strftime('%I:%M %p') if isinstance(dtstart, datetime) else None,
                'opponent': opponent,
                'location': location,
                'home_away': home_away,
                'tv': tv,
                'result': result
            })

        return events

    def get_games_for_date(self, date: datetime.date, team: str = 'both') -> List[Dict]:
        """
        Get games scheduled for a specific date.

        Args:
            date: Date to check
            team: 'mens', 'womens', or 'both' (default)

        Returns:
            List of games on that date
        """
        games = []

        # Check men's schedule
        if team in ('mens', 'both'):
            mbb_file = self.sports_dir / 'duke-mbb-25-26.ics'
            if mbb_file.exists():
                events = self.parse_ics_file(mbb_file)
                for event in events:
                    if event['date'] == date:
                        event['team'] = "Men's Basketball"
                        games.append(event)

        # Check women's schedule
        if team in ('womens', 'both'):
            wbb_file = self.sports_dir / 'duke-wbb-25-26.ics'
            if wbb_file.exists():
                events = self.parse_ics_file(wbb_file)
                for event in events:
                    if event['date'] == date:
                        event['team'] = "Women's Basketball"
                        games.append(event)

        return games

    def get_upcoming_games(self, start_date: datetime.date, days: int = 7) -> List[Dict]:
        """
        Get all games in the next N days.

        Args:
            start_date: Start date
            days: Number of days to look ahead

        Returns:
            List of games with 'date', 'team', 'opponent', etc.
        """
        games = []

        for i in range(days):
            date = start_date + timedelta(days=i)
            games.extend(self.get_games_for_date(date))

        return sorted(games, key=lambda g: g['date'])

    def format_game_box(self, game: Dict) -> Dict:
        """
        Format a game as a feature box.

        Args:
            game: Game dict from get_games_for_date()

        Returns:
            Dict with 'title' and 'content' for feature box
        """
        # Title: "Duke [Men's/Women's] Basketball"
        title = f"🏀 Duke {game['team']}"

        # Content: Date, Time, Opponent, Location, TV (as HTML)
        lines = []

        # Format date nicely
        date_str = game['date'].strftime('%A, %B %-d')
        lines.append(f"<strong>{date_str}</strong><br>")

        if game['time']:
            lines.append(f"{game['time']} PT<br>")

        # Opponent with home/away
        if game['home_away'] == 'Home':
            lines.append(f"vs <strong>{game['opponent']}</strong><br>")
            if 'Cameron Indoor Stadium' in game['location']:
                lines.append("Cameron Indoor Stadium<br>")
        else:
            lines.append(f"at <strong>{game['opponent']}</strong><br>")

        # TV info
        if game['tv']:
            lines.append(f"📺 {game['tv']}<br>")

        # Result if game is in the past
        if game['result']:
            lines.append(f"<br><em>{game['result']}</em>")

        content = '\n'.join(lines)

        return {
            'title': title,
            'content': content
        }


if __name__ == '__main__':
    # Test the schedule parser
    print("🏀 Testing Duke Basketball Schedule Parser\n")

    schedule = DukeBasketballSchedule()

    # Test with today
    today = datetime.now().date()
    print(f"Games today ({today}):")
    games_today = schedule.get_games_for_date(today)
    if games_today:
        for game in games_today:
            print(f"  {game['team']}: {game['home_away']} vs {game['opponent']}")
    else:
        print("  No games today")

    # Test with upcoming week
    print(f"\nGames in next 7 days:")
    upcoming = schedule.get_upcoming_games(today, days=7)
    if upcoming:
        for game in upcoming:
            print(f"  {game['date']}: {game['team']} - {game['home_away']} vs {game['opponent']}")
            box = schedule.format_game_box(game)
            print(f"    Box title: {box['title']}")
    else:
        print("  No games in next 7 days")
