<!--
SPDX-FileCopyrightText: 2025 Luis Villa <luis@lu.is>

SPDX-License-Identifier: BlueOak-1.0.0
-->

# Sports Schedule Data

This directory contains sports schedule data in ICS (iCalendar) format.

## Duke Basketball Schedules

The Duke basketball schedules can be downloaded from GoDuke.com:

### Men's Basketball
- **2025-26 Season**: https://goduke.com/calendar.aspx/export_fullcalendar?sport_id=7&start=2025-07-01&end=2026-06-30
- Save as: `duke-mbb-25-26.ics`

### Women's Basketball
- **2025-26 Season**: https://goduke.com/calendar.aspx/export_fullcalendar?sport_id=18&start=2025-07-01&end=2026-06-30
- Save as: `duke-wbb-25-26.ics`

## Usage

The sports schedule module (`code/src/sports_schedule.py`) reads these ICS files to check for upcoming games and add them to the newspaper's feature box.

## License Note

These schedule files are provided by Duke Athletics and are not part of this repository's license. They should not be committed to version control.
