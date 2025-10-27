# Claude Development Notes

## Project Overview
Automated SMS school schedule system using GitHub Actions and Textbelt API.

## Development Guidelines

### Testing Commands
Before making changes, always test locally:
```bash
# Test today's schedule (prints to console)
python3 rotate_days.py --today

# Test SMS functionality (uses local .env)
python3 rotate_days.py --sms-today

# Test specific dates
python3 rotate_days.py --check 2025-01-15
```

### Environment Setup
- Local development uses `.env` file (git-ignored)
- GitHub Actions uses repository secrets
- Always test locally before pushing changes

### Key Configuration Points
- `ANCHOR_DATE` and `ANCHOR_CYCLE`: Set once per school year
- `LIBRARY_DAYS`: Update when student schedules change
- `ICS_URL`: School calendar feed URL
- Cron schedules in workflow file for SMS timing

### Deployment Process
1. Test changes locally
2. Commit and push to GitHub
3. GitHub Actions automatically runs on schedule
4. Monitor Actions tab for any failures

### Important Notes
- Timezone handling: All calculations in Eastern Time
- SMS costs ~$0.01 each via Textbelt
- Free GitHub Actions quota is sufficient for this use case
- Manual off-days are stored in `manual_off_days.yaml` (git-tracked)

### Common Changes
- **Add snow day**: Use `--add-off` command, then commit the YAML file
- **Update student library days**: Edit `LIBRARY_DAYS` dictionary
- **Change SMS times**: Modify cron schedules in workflow file
- **New school year**: Update `ANCHOR_DATE` and `ANCHOR_CYCLE`

### Error Handling
- Script falls back to printing if SMS fails
- GitHub Actions will show detailed logs for troubleshooting
- Textbelt quota warnings are displayed in output