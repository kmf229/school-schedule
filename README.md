# School Schedule SMS Reminder

Automated SMS notifications for a 5-day rotating school schedule with library reminders and event notifications.

## Features

- **Automated SMS notifications** via GitHub Actions
- **5-day cycle tracking** with automatic progression
- **Library day reminders** for specific students
- **School event integration** from ICS calendar feed
- **Manual off-day support** for snow days, holidays, etc.
- **Timezone-aware** scheduling (Eastern Time)

## Schedule

- **6:00 AM weekdays**: Today's cycle day, library reminders, and events
- **7:00 PM weeknights**: Tomorrow's schedule for planning ahead

## Setup

### Requirements
- GitHub account
- Textbelt API key (~$0.01 per SMS)
- Python 3.8+ (for local testing)

### Installation

1. Clone this repository
2. Install dependencies: `pip install ics python-dateutil pyyaml requests python-dotenv`
3. Get a Textbelt API key from [textbelt.com](https://textbelt.com)
4. Add GitHub secrets:
   - `TEXTBELT_API_KEY`: Your Textbelt API key
   - `TO_PHONE_NUMBER`: Your phone number (format: +1234567890)

### Configuration

Edit the configuration section in `rotate_days.py`:

```python
# School calendar ICS URL
ICS_URL = "https://your-school.com/calendar.ics"

# First instructional day and its cycle
ANCHOR_DATE = date(2025, 9, 2)   # Adjust to your school year
ANCHOR_CYCLE = 1                 # What cycle day was the anchor date

# Library day assignments
LIBRARY_DAYS = {
    "Student Name (Day X library)": {X},  # Replace with actual students
}
```

## Usage

### Manual Commands

```bash
# Check today's schedule
python3 rotate_days.py --today

# Check tomorrow's schedule  
python3 rotate_days.py --tomorrow

# Send SMS for today
python3 rotate_days.py --sms-today

# Check a specific date
python3 rotate_days.py --check 2025-01-15

# Add a snow day / manual off-day
python3 rotate_days.py --add-off 2025-01-15

# List all manual off-days
python3 rotate_days.py --list-off

# Show events only for a date
python3 rotate_days.py --events 2025-01-15
```

### Adding Snow Days

When school is cancelled:

1. Add the off-day: `python3 rotate_days.py --add-off 2025-01-15`
2. Commit to GitHub: 
   ```bash
   git add manual_off_days.yaml
   git commit -m "Add snow day"
   git push
   ```

The system automatically adjusts cycle calculations to account for the missed day.

## How It Works

### Cycle Day Calculation
- Starts from an anchor date with a known cycle day
- Counts only instructional days (skips weekends and no-school days)
- Progresses through a 5-day rotation (1→2→3→4→5→1...)

### No-School Day Detection
- Automatically detects holidays/closures from ICS calendar
- Manual override via YAML file for snow days
- Configurable patterns for detecting no-school events

### Event Processing
- Fetches events from school's ICS calendar feed
- Filters and formats events for the target date
- Handles both all-day and timed events
- Timezone conversion for accurate date matching

## Files

- `rotate_days.py`: Main script with all functionality
- `events.ics`: Local copy of school calendar (fetched automatically)
- `manual_off_days.yaml`: Manual no-school days (git-tracked)
- `.env`: Local environment variables (git-ignored)
- `.github/workflows/schedule-sms.yml`: GitHub Actions automation

## Cost

Approximately $5-7 per year for SMS (2 messages/day × ~180 school days × $0.01/SMS)

## Troubleshooting

- **No SMS received**: Check GitHub Actions logs and Textbelt quota
- **Wrong cycle day**: Verify anchor date and check for missing off-days  
- **Missing events**: Confirm ICS URL is accessible and events have proper formatting
- **Timezone issues**: All times are calculated in Eastern Time (America/New_York)

## License

MIT License - feel free to adapt for your own school schedule!